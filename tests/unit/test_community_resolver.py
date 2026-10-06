"""Unit Tests for CommunityResolutionService & Two-Tier Disambiguation Engine

涵蓋：
1. 本地快速對齊 (0 網路請求)
2. 遠端兩層式探索與入庫 (坐標保證與外鍵回填)
3. 嚴格消歧比對 (多候選歧義略過、無社區略過)
4. 乾跑預演模式 (dry-run 零寫入驗證)
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy import select

from src.core.registry import ProviderRegistry
from src.domain.common import GeoPoint, PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.sale_house import NormalizedSaleListing
from src.services.community_resolver import (
    CommunityResolutionOptions,
    CommunityResolutionService,
    MatchStatus,
)
from src.storage.database import DatabaseManager
from src.storage.models.community import CommunityTable
from src.storage.models.property import PropertyTable
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.property_repo import PropertyRepository


from src.core.interfaces.provider import IHouseSourceProvider


@pytest_asyncio.fixture
async def resolver_test_db():
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


class DummyCommunityProvider(IHouseSourceProvider):
    def __init__(self, community_service):
        self._comm = community_service

    @property
    def provider_id(self) -> str:
        return "591"

    @property
    def provider_name(self) -> str:
        return "591房屋交易"

    @property
    def community(self):
        return self._comm

    @property
    def sale_house(self):
        return None

    @property
    def new_house(self):
        return None

    @property
    def diagnostics(self):
        return None

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_local_reconciliation_by_external_id(resolver_test_db: DatabaseManager):
    """測試第一階段：本地已有相同外部代碼之社區時，0 次網路請求直接回填外鍵"""
    async with resolver_test_db.session() as session:
        comm_repo = CommunityRepository(session)
        prop_repo = PropertyRepository(session)

        # 1. 建立既有社區節點
        comm_detail = NormalizedCommunityDetail(
            provider_id="591",
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            region_name="台北市",
            section_name="松山區",
            address="台北市松山區延壽街",
        )
        saved_comm = await comm_repo.upsert_from_detail(comm_detail, provider_id="591")

        # 2. 建立帶有 external_community_id 但 community_uuid 為 None 的房屋
        prop = await prop_repo.upsert_from_summary(
            NormalizedSaleListing(
                provider_id="591",
                external_house_id="S1001",
                title="鳴森大苑三房",
                price_wan=5000,
                total_area_pin=45.0,
                region_name="台北市",
                section_name="松山區",
                external_community_id="5855864",
                community_name="鳴森大苑-碧硯閣",
            ),
            provider_id="591",
        )
        # 人為清除外鍵模擬未綁定狀態
        prop.community_uuid = None
        await session.flush()

    # Mock Provider: 驗證完全不應被調用
    mock_comm_provider = MagicMock()
    mock_comm_provider.search_communities = AsyncMock()
    mock_comm_provider.get_community_detail = AsyncMock()

    reg = ProviderRegistry()
    reg.register_instance(DummyCommunityProvider(mock_comm_provider))

    service = CommunityResolutionService(provider_registry=reg, database=resolver_test_db)
    options = CommunityResolutionOptions(provider_id="591")
    report = await service.resolve_unlinked_properties(options)

    # 驗證本地命中且零網路請求
    assert report.scanned_properties_count == 1
    assert report.locally_linked_properties_count == 1
    assert report.remotely_resolved_properties_count == 0
    mock_comm_provider.search_communities.assert_not_called()
    mock_comm_provider.get_community_detail.assert_not_called()

    # 驗證外鍵成功更新
    async with resolver_test_db.session() as session:
        stmt = select(PropertyTable).where(PropertyTable.external_house_id == "S1001")
        res = await session.execute(stmt)
        updated_prop = res.scalar_one()
        assert updated_prop.community_uuid == saved_comm.id


@pytest.mark.asyncio
async def test_remote_two_tier_discovery_and_persistence(resolver_test_db: DatabaseManager):
    """測試第二階段：遠端兩層式清單探索與入庫，驗證坐標存在且外鍵回填"""
    async with resolver_test_db.session() as session:
        prop_repo = PropertyRepository(session)
        # 建立僅有 community_name 的房屋
        prop = await prop_repo.upsert_from_summary(
            NormalizedSaleListing(
                provider_id="591",
                external_house_id="S2002",
                title="國美新美館高樓景觀戶",
                price_wan=8800,
                total_area_pin=60.0,
                region_name="台北市",
                section_name="信義區",
                community_name="國美新美館",
            ),
            provider_id="591",
        )
        prop.community_uuid = None
        prop.external_community_id = None
        await session.flush()

    # Mock Provider 實作兩層式回應
    mock_comm_provider = MagicMock()

    # 1. 第一層清單回傳：具備坐標與身分
    summary_candidate = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="5900888",
        community_name="國美新美館",
        region_name="台北市",
        section_name="信義區",
        address="台北市信義區松德路200號",
        coordinates=GeoPoint(lat=25.0345, lng=121.5712),
        cover_image_url="https://img.example.com/cover.jpg",
    )

    async def mock_search(q: CommunitySearchQuery):
        assert q.keywords == "國美新美館"
        assert q.region_id == 1  # 台北市代碼
        return PageResult.create(items=[summary_candidate], total_records=1, page=1, page_size=20)

    # 2. 第二層詳情回傳：具備深層建材與車位規格
    async def mock_detail(ext_id: str, summary: NormalizedCommunitySummary):
        assert ext_id == "5900888"
        assert summary.coordinates is not None
        return NormalizedCommunityDetail(
            provider_id="591",
            external_community_id=ext_id,
            community_name=summary.community_name,
            region_name=summary.region_name,
            section_name=summary.section_name,
            address=summary.address,
            coordinates=summary.coordinates,
            total_households=150,
            base_area_pin=500.0,
        )

    mock_comm_provider.search_communities = AsyncMock(side_effect=mock_search)
    mock_comm_provider.get_community_detail = AsyncMock(side_effect=mock_detail)

    reg = ProviderRegistry()
    reg.register_instance(DummyCommunityProvider(mock_comm_provider))

    service = CommunityResolutionService(provider_registry=reg, database=resolver_test_db)
    options = CommunityResolutionOptions(provider_id="591")
    report = await service.resolve_unlinked_properties(options)

    # 驗證遠端解析統計
    assert report.scanned_properties_count == 1
    assert report.remotely_resolved_properties_count == 1
    assert report.persisted_communities_count == 1

    # 驗證資料庫 Communities 表完整寫入且坐標保留
    async with resolver_test_db.session() as session:
        c_stmt = select(CommunityTable).where(CommunityTable.external_community_id == "5900888")
        c_res = await session.execute(c_stmt)
        saved_comm = c_res.scalar_one()
        assert saved_comm.name == "國美新美館"
        assert saved_comm.lat == 25.0345
        assert saved_comm.lng == 121.5712
        assert saved_comm.base_area_pin == 500.0

        # 驗證房屋主表外鍵與外部社區 ID 成功更新
        p_stmt = select(PropertyTable).where(PropertyTable.external_house_id == "S2002")
        p_res = await session.execute(p_stmt)
        updated_prop = p_res.scalar_one()
        assert updated_prop.community_uuid == saved_comm.id
        assert updated_prop.external_community_id == "5900888"


@pytest.mark.asyncio
async def test_strict_disambiguation_ambiguous_skipping(resolver_test_db: DatabaseManager):
    """測試消歧防護：同區存在多個同名不同代碼社區時，主動標記 AMBIGUOUS 並略過，防止誤配"""
    async with resolver_test_db.session() as session:
        prop_repo = PropertyRepository(session)
        prop = await prop_repo.upsert_from_summary(
            NormalizedSaleListing(
                provider_id="591",
                external_house_id="S3003",
                title="大安花園兩房",
                price_wan=3000,
                total_area_pin=30.0,
                region_name="台北市",
                section_name="大安區",
                community_name="大安花園",
            ),
            provider_id="591",
        )
        prop.community_uuid = None
        await session.flush()

    # 模擬遠端搜尋回傳 2 個同名但在不同地址的社區代碼
    mock_comm_provider = MagicMock()
    cand1 = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="500001",
        community_name="大安花園",
        region_name="台北市",
        section_name="大安區",
        address="台北市大安區新生南路一段",
    )
    cand2 = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="500002",
        community_name="大安花園",
        region_name="台北市",
        section_name="大安區",
        address="台北市大安區和平東路二段",
    )

    async def mock_search(q: CommunitySearchQuery):
        return PageResult.create(items=[cand1, cand2], total_records=2, page=1, page_size=20)

    mock_comm_provider.search_communities = AsyncMock(side_effect=mock_search)
    mock_comm_provider.get_community_detail = AsyncMock()

    reg = ProviderRegistry()
    reg.register_instance(DummyCommunityProvider(mock_comm_provider))

    service = CommunityResolutionService(provider_registry=reg, database=resolver_test_db)
    options = CommunityResolutionOptions(provider_id="591")
    report = await service.resolve_unlinked_properties(options)

    # 驗證歧義被安全略過
    assert report.ambiguous_targets_count == 1
    assert report.remotely_resolved_properties_count == 0
    mock_comm_provider.get_community_detail.assert_not_called()

    # 房屋仍保持 NULL，未被錯誤綁定
    async with resolver_test_db.session() as session:
        p_stmt = select(PropertyTable).where(PropertyTable.external_house_id == "S3003")
        p_res = await session.execute(p_stmt)
        p = p_res.scalar_one()
        assert p.community_uuid is None


@pytest.mark.asyncio
async def test_dry_run_mode_leaves_database_unmodified(resolver_test_db: DatabaseManager):
    """測試乾跑模式 (dry_run=True)：產出完整比對報告，但資料庫零變更"""
    async with resolver_test_db.session() as session:
        prop_repo = PropertyRepository(session)
        prop = await prop_repo.upsert_from_summary(
            NormalizedSaleListing(
                provider_id="591",
                external_house_id="S4004",
                title="敦南名邸四房",
                price_wan=6000,
                total_area_pin=55.0,
                region_name="台北市",
                section_name="大安區",
                community_name="敦南名邸",
            ),
            provider_id="591",
        )
        prop.community_uuid = None
        await session.flush()

    mock_comm_provider = MagicMock()
    cand = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="599999",
        community_name="敦南名邸",
        region_name="台北市",
        section_name="大安區",
        address="台北市大安區敦化南路",
    )
    mock_comm_provider.search_communities = AsyncMock(
        return_value=PageResult.create(items=[cand], total_records=1, page=1, page_size=20)
    )
    mock_comm_provider.get_community_detail = AsyncMock(
        return_value=NormalizedCommunityDetail(
            provider_id="591",
            external_community_id="599999",
            community_name="敦南名邸",
            region_name="台北市",
            section_name="大安區",
            address="台北市大安區敦化南路",
        )
    )

    reg = ProviderRegistry()
    reg.register_instance(DummyCommunityProvider(mock_comm_provider))

    service = CommunityResolutionService(provider_registry=reg, database=resolver_test_db)
    options = CommunityResolutionOptions(provider_id="591", dry_run=True)
    report = await service.resolve_unlinked_properties(options)

    # 驗證報告顯示遠端匹配，但資料庫無變更
    assert report.remotely_resolved_properties_count == 1
    assert report.persisted_communities_count == 1

    async with resolver_test_db.session() as session:
        # Communities 表無新寫入
        c_stmt = select(CommunityTable).where(CommunityTable.external_community_id == "599999")
        c_res = await session.execute(c_stmt)
        assert c_res.scalar_one_or_none() is None

        # 房屋外鍵依然為 NULL
        p_stmt = select(PropertyTable).where(PropertyTable.external_house_id == "S4004")
        p_res = await session.execute(p_stmt)
        assert p_res.scalar_one().community_uuid is None
