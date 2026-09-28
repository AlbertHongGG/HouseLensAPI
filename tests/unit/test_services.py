"""Unit Tests for HouseLensAPI Aggregator & Deduplication Services"""

import pytest
import pytest_asyncio

from src.core.registry import registry
from src.domain.common import GeoPoint, PageResult
from src.domain.community import CommunitySearchQuery, CommunitySummary
from src.domain.new_house import NewHouseSearchQuery, NewHouseSummary
from src.domain.sale_house import SaleHouseSearchQuery, SaleHouseSummary
from src.services.aggregator import HouseAggregatorService
from src.services.deduplication import (
    PropertyDeduplicationService,
    is_area_compatible,
    is_layout_compatible,
    normalize_floor,
)
from src.storage.database import DatabaseManager
from src.storage.repositories.property_repo import PropertyRepository


@pytest_asyncio.fixture
async def service_test_db():
    """建立獨立的非同步 SQLite 記憶體資料庫供服務層測試"""
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


def test_dedup_helper_functions():
    """測試樓層正規化、格局相容性與坪數誤差比對輔助函式"""
    # 1. 樓層正規化
    assert normalize_floor("2F/24F") == "2"
    assert normalize_floor("2樓") == "2"
    assert normalize_floor("2") == "2"
    assert normalize_floor("15F") == "15"
    assert normalize_floor(None) is None

    # 2. 格局相容性
    assert is_layout_compatible("3房2廳2衛", "3房2廳") is True
    assert is_layout_compatible("3房2廳", "3房2廳2衛") is True
    assert is_layout_compatible("2房1廳", "3房2廳") is False
    assert is_layout_compatible("開放格局", "開放格局") is True

    # 3. 坪數誤差容忍度 (±2%)
    assert is_area_compatible(46.29, 46.30, tolerance_pct=0.02) is True
    assert is_area_compatible(46.29, 47.00, tolerance_pct=0.02) is True  # ~1.5%
    assert is_area_compatible(46.29, 52.00, tolerance_pct=0.02) is False  # >10%


@pytest.mark.asyncio
async def test_deduplication_service_candidate_evaluation(service_test_db: DatabaseManager):
    """測試去重評估服務在資料庫存在候選物件時的信心度計分"""
    dedup = PropertyDeduplicationService(area_tolerance_pct=0.02)

    async with service_test_db.session() as session:
        repo = PropertyRepository(session)

        # 寫入第一筆物件
        base_summary = SaleHouseSummary(
            house_id="A1001",
            title="鳴森大苑景觀高樓3房",
            price="5,258萬元",
            total_area=46.29,
            layout="3房2廳",
            region="台北市",
            section="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor="2",
        )
        await repo.upsert_from_summary(base_summary, provider_id="provider_a")

        # 評估相符度極高之物件 (同社區、同樓層、坪數 46.30、格局相容)
        cand_duplicate = SaleHouseSummary(
            house_id="B2002",
            title="碧硯閣二樓三房優質釋出",
            price="5,300萬元",
            total_area=46.30,
            layout="3房2廳2衛",
            region="台北市",
            section="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor="2F/24F",
        )
        res_dup = await dedup.evaluate_candidate(cand_duplicate, repo)
        assert res_dup.is_duplicate is True
        assert res_dup.confidence_score >= 0.7
        assert len(res_dup.match_reasons) >= 3

        # 評估不同樓層物件 (同社區，但 10 樓)
        cand_different_floor = SaleHouseSummary(
            house_id="C3003",
            title="碧硯閣十樓三房",
            price="5,800萬元",
            total_area=46.29,
            layout="3房2廳",
            region="台北市",
            section="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor="10",
        )
        res_diff = await dedup.evaluate_candidate(cand_different_floor, repo)
        assert res_diff.is_duplicate is False


@pytest.mark.asyncio
async def test_aggregator_service_sync_and_search_flow(service_test_db: DatabaseManager):
    """測試聚合服務從 591 同步社區、中古屋與新建案至本地資料庫並檢索"""
    service = HouseAggregatorService(
        provider_registry=registry,
        database=service_test_db,
    )

    # 1. 同步社區 (限定 2 筆，含詳情)
    comm_query = CommunitySearchQuery(region_id=1, page=1, page_size=2)
    synced_comms = await service.sync_communities(
        provider_id="591",
        query=comm_query,
        sync_details=True,
        max_items=2,
    )
    assert len(synced_comms) == 2
    for c in synced_comms:
        assert c.id is not None
        assert c.name != ""

    # 在庫查詢社區
    found_comms = await service.search_communities(region="台北市")
    assert len(found_comms) >= 2

    # 2. 同步中古屋 (限定 2 筆，含詳情與去重)
    sh_query = SaleHouseSearchQuery(region_id=1, page=1)
    synced_props = await service.sync_sale_houses(
        provider_id="591",
        query=sh_query,
        sync_details=True,
        max_items=2,
    )
    assert len(synced_props) == 2
    for p in synced_props:
        assert p.id is not None
        assert p.price > 0

    # 在庫查詢房屋物件
    found_props = await service.search_properties(region="台北市")
    assert len(found_props) >= 2

    # 3. 同步新建案 (限定 2 筆，含詳情 layout_v2)
    nh_query = NewHouseSearchQuery(region_id=1, page=1, page_size=2)
    synced_nhs = await service.sync_new_houses(
        provider_id="591",
        query=nh_query,
        sync_details=True,
        max_items=2,
    )
    assert len(synced_nhs) == 2
    for nh in synced_nhs:
        assert nh.id is not None
        assert nh.project_name != ""

    # 在庫查詢新建案
    found_nhs = await service.search_new_houses(region="台北市")
    assert len(found_nhs) >= 2
