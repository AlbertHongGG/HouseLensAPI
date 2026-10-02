"""HouseLensAPI - 同步協調應用案例單元測試 (Unit Tests for SyncUseCase)"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from src.application.progress import SilentProgressReporter
from src.application.sync_usecase import SyncOptions, SyncUseCase
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.registry import ProviderRegistry
from src.domain.common import PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NewHouseSearchQuery,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.storage.database import DatabaseManager


class DummyProvider(IHouseSourceProvider):
    """測試專用 Mock Provider"""

    def __init__(self, comm=None, sale=None, new_h=None):
        self._comm = comm
        self._sale = sale
        self._new_h = new_h

    @property
    def provider_id(self) -> str:
        return "mock_591"

    @property
    def provider_name(self) -> str:
        return "Mock 591"

    @property
    def community(self):
        return self._comm

    @property
    def sale_house(self):
        return self._sale

    @property
    def new_house(self):
        return self._new_h

    @property
    def diagnostics(self):
        return None

    async def health_check(self) -> bool:
        return True


@pytest_asyncio.fixture
async def sync_test_db():
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_sync_sale_houses_multi_page_accumulation(sync_test_db: DatabaseManager):
    """驗證中古屋同步能透過累加器跨頁抓取並精確累積至指定目標筆數"""
    mock_sale_service = MagicMock()

    # 模擬每頁 10 筆，共 30 筆
    async def mock_search(query: SaleHouseSearchQuery) -> PageResult[NormalizedSaleListing]:
        items = [
            NormalizedSaleListing(
                provider_id="mock_591",
                external_house_id=f"H_{(query.page - 1) * 10 + i}",
                title=f"測試房屋_{(query.page - 1) * 10 + i}",
                price_wan=2500,
                unit_price_wan=80.0,
                total_area_pin=31.25,
                region="台北市",
                section="大安區",
                address="台北市大安區和平東路二段",
                rooms=3,
                living_rooms=2,
                bathrooms=2,
            )
            for i in range(10)
        ]
        return PageResult.create(items=items, total_records=30, page=query.page, page_size=10)

    async def mock_detail(house_id: str) -> NormalizedSalePropertyDetail:
        return NormalizedSalePropertyDetail(
            external_house_id=house_id,
            title=f"詳細規格_{house_id}",
            price_wan=2500,
            unit_price_wan=80.0,
            total_area_pin=31.25,
            main_area_pin=22.0,
            address="台北市大安區和平東路二段",
            building_age_years=5.0,
        )

    mock_sale_service.search_sale_houses = AsyncMock(side_effect=mock_search)
    mock_sale_service.get_sale_house_detail = AsyncMock(side_effect=mock_detail)

    reg = ProviderRegistry()
    reg.register_instance(DummyProvider(sale=mock_sale_service))

    uc = SyncUseCase(
        provider_registry=reg,
        database=sync_test_db,
    )

    # 測試要求 25 筆 (需跨越第 1 頁 10 筆、第 2 頁 10 筆、第 3 頁前 5 筆)
    query = SaleHouseSearchQuery(region_id=1, page_size=10)
    synced = await uc.sync_sale_houses(
        provider_id="mock_591",
        query=query,
        max_items=25,
        concurrency=2,
        reporter=SilentProgressReporter(),
    )

    assert len(synced) == 25
    assert mock_sale_service.search_sale_houses.call_count == 3
    assert mock_sale_service.get_sale_house_detail.call_count == 25


@pytest.mark.asyncio
async def test_sync_communities_multi_page_accumulation(sync_test_db: DatabaseManager):
    """驗證社區同步能跨頁抓取並精確累積至指定目標筆數"""
    mock_comm_service = MagicMock()

    async def mock_search(query: CommunitySearchQuery) -> PageResult[NormalizedCommunitySummary]:
        items = [
            NormalizedCommunitySummary(
                community_id=f"C_{(query.page - 1) * 10 + i}",
                community_name=f"測試社區_{(query.page - 1) * 10 + i}",
                region_name="台北市",
                section_name="信義區",
                full_address="台北市信義區信義路五段",
            )
            for i in range(10)
        ]
        return PageResult.create(items=items, total_records=40, page=query.page, page_size=10)

    async def mock_detail(comm_id: str) -> NormalizedCommunityDetail:
        return NormalizedCommunityDetail(
            community_id=comm_id,
            community_name=f"詳情_{comm_id}",
            address="台北市信義區信義路五段",
            region_name="台北市",
            section_name="信義區",
            total_households=150,
        )

    mock_comm_service.search_communities = AsyncMock(side_effect=mock_search)
    mock_comm_service.get_community_detail = AsyncMock(side_effect=mock_detail)

    reg = ProviderRegistry()
    reg.register_instance(DummyProvider(comm=mock_comm_service))

    uc = SyncUseCase(
        provider_registry=reg,
        database=sync_test_db,
    )

    # 抓取 15 筆 (第 1 頁 10 筆 + 第 2 頁前 5 筆)
    query = CommunitySearchQuery(region_id=1, page_size=10)
    synced = await uc.sync_communities(
        provider_id="mock_591",
        query=query,
        max_items=15,
        concurrency=2,
        reporter=SilentProgressReporter(),
    )

    assert len(synced) == 15
    assert mock_comm_service.search_communities.call_count == 2
    assert mock_comm_service.get_community_detail.call_count == 15


@pytest.mark.asyncio
async def test_sync_new_houses_multi_page_accumulation(sync_test_db: DatabaseManager):
    """驗證新建案同步能跨頁抓取並精確累積至指定目標筆數"""
    mock_new_service = MagicMock()

    async def mock_search(query: NewHouseSearchQuery) -> PageResult[NormalizedNewHouseSummary]:
        items = [
            NormalizedNewHouseSummary(
                source_hid=1000 + (query.page - 1) * 10 + i,
                project_name=f"測試建案_{(query.page - 1) * 10 + i}",
                project_status="預售屋",
                region_name="台北市",
                section_name="南港區",
                address="台北市南港區重陽路",
            )
            for i in range(10)
        ]
        return PageResult.create(items=items, total_records=50, page=query.page, page_size=10)

    async def mock_detail(new_house_id: str) -> NormalizedNewHouseDetail:
        return NormalizedNewHouseDetail(
            hid=int(new_house_id),
            project_name=f"詳情_{new_house_id}",
            build_type="預售屋",
            region="台北市",
            section="南港區",
            address="台北市南港區重陽路",
            total_households=120,
        )

    mock_new_service.search_new_houses = AsyncMock(side_effect=mock_search)
    mock_new_service.get_new_house_detail = AsyncMock(side_effect=mock_detail)

    reg = ProviderRegistry()
    reg.register_instance(DummyProvider(new_h=mock_new_service))

    uc = SyncUseCase(
        provider_registry=reg,
        database=sync_test_db,
    )

    # 抓取 22 筆 (第 1 頁 10 筆 + 第 2 頁 10 筆 + 第 3 頁前 2 筆)
    query = NewHouseSearchQuery(region_id=1, page_size=10)
    synced = await uc.sync_new_houses(
        provider_id="mock_591",
        query=query,
        max_items=22,
        concurrency=2,
        reporter=SilentProgressReporter(),
    )

    assert len(synced) == 22
    assert mock_new_service.search_new_houses.call_count == 3
    assert mock_new_service.get_new_house_detail.call_count == 22


@pytest.mark.asyncio
async def test_sync_all_with_unified_options(sync_test_db):
    """驗證 sync_all 能透過 SyncOptions 解耦分派查詢物件並順利同步三大領域"""
    # 1. Mock Community Service
    mock_comm = MagicMock()
    async def mock_search_comm(q: CommunitySearchQuery):
        assert q.region_id == 1
        assert q.keywords == "精選"
        assert q.max_age_years == 10.0
        items = [
            NormalizedCommunitySummary(
                community_id=f"C_{i}",
                community_name=f"社區_{i}",
                region_name="台北市",
                section_name="信義區",
                full_address="台北市信義區信義路",
            )
            for i in range(5)
        ]
        return PageResult.create(items=items, total_records=5, page=q.page, page_size=q.page_size)

    async def mock_detail_comm(cid: str):
        return NormalizedCommunityDetail(
            community_id=cid,
            community_name=f"社區_{cid}",
            address="台北市信義區信義路",
            region_name="台北市",
            section_name="信義區",
        )

    mock_comm.search_communities = AsyncMock(side_effect=mock_search_comm)
    mock_comm.get_community_detail = AsyncMock(side_effect=mock_detail_comm)

    # 2. Mock Sale House Service
    mock_sale = MagicMock()
    async def mock_search_sale(q: SaleHouseSearchQuery):
        assert q.region_id == 1
        assert q.keywords == "精選"
        assert q.max_age_years == 10.0
        assert q.min_price_wan == 2000
        items = [
            NormalizedSaleListing(
                provider_id="mock_591",
                external_house_id=f"S_{i}",
                title=f"中古屋_{i}",
                price_wan=2500,
                unit_price_wan=80.0,
                total_area_pin=31.25,
                region="台北市",
                section="大安區",
            )
            for i in range(5)
        ]
        return PageResult.create(items=items, total_records=5, page=q.page, page_size=q.page_size)

    async def mock_detail_sale(hid: str):
        return NormalizedSalePropertyDetail(
            external_house_id=hid,
            provider_id="mock_591",
            title=f"中古屋_{hid}",
            price_wan=2500,
            region_name="台北市",
            section_name="大安區",
            full_address="台北市大安區和平東路",
            building_age_years=6.0,
        )

    mock_sale.search_sale_houses = AsyncMock(side_effect=mock_search_sale)
    mock_sale.get_sale_property_detail = AsyncMock(side_effect=mock_detail_sale)

    # 3. Mock New House Service
    mock_new = MagicMock()
    async def mock_search_new(q: NewHouseSearchQuery):
        assert q.region_id == 1
        assert q.keywords == "精選"
        # 關鍵驗證：NewHouseSearchQuery 不具備 max_age_years 與 min_price_wan，已自然解耦忽略
        assert not hasattr(q, "max_age_years")
        assert not hasattr(q, "min_price_wan")
        items = [
            NormalizedNewHouseSummary(
                source_hid=9000 + i,
                project_name=f"建案_{i}",
                project_status="新成屋",
                region_name="台北市",
                section_name="中山區",
                address="台北市中山區民生東路",
            )
            for i in range(5)
        ]
        return PageResult.create(items=items, total_records=5, page=q.page, page_size=q.page_size)

    async def mock_detail_new(hid: str):
        return NormalizedNewHouseDetail(
            hid=int(hid),
            project_name=f"建案_{hid}",
            build_type="新成屋",
            region="台北市",
            section="中山區",
            address="台北市中山區民生東路",
        )

    mock_new.search_new_houses = AsyncMock(side_effect=mock_search_new)
    mock_new.get_new_house_detail = AsyncMock(side_effect=mock_detail_new)

    reg = ProviderRegistry()
    reg.register_instance(DummyProvider(comm=mock_comm, sale=mock_sale, new_h=mock_new))

    uc = SyncUseCase(provider_registry=reg, database=sync_test_db)

    # 呼叫 sync_all 帶入包含屋齡、關鍵字、價格等全域參數
    options = SyncOptions(
        provider_id="mock_591",
        region_id=1,
        keywords="精選",
        max_age_years=10.0,
        min_price_wan=2000,
        limit=5,
        concurrency=2,
    )
    result = await uc.sync_all(options=options, reporter=SilentProgressReporter())

    assert len(result["communities"]) == 5
    assert len(result["sale_houses"]) == 5
    assert len(result["new_houses"]) == 5
    assert mock_comm.search_communities.call_count == 1
    assert mock_sale.search_sale_houses.call_count == 1
    assert mock_new.search_new_houses.call_count == 1
