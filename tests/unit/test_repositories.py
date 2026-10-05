"""Unit Tests for HouseLensAPI Storage Repositories & Database Layer"""

import pytest
import pytest_asyncio

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NewHouseLayoutSpec,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.storage.database import DatabaseManager
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.new_house_repo import NewHouseRepository
from src.storage.repositories.property_repo import PropertyRepository


@pytest_asyncio.fixture
async def test_db():
    """建立獨立的非同步 SQLite 記憶體資料庫"""
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_community_repository_upsert_and_search(test_db: DatabaseManager):
    """測試社區 Summary 與 Detail 之寫入、合併與檢索"""
    async with test_db.session() as session:
        repo = CommunityRepository(session)

        # 1. 從 Summary 寫入
        summary = NormalizedCommunitySummary(
            provider_id="591",
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            build_purpose="住宅",
            building_type="住宅大樓",
            housing_status="新成屋",
            region_name="台北市",
            section_name="松山區",
            address="台北市松山區延壽街76之1號",
            coordinates=GeoPoint(lat=25.0569, lng=121.5651),
            avg_unit_price_wan=129.0,
            building_age_years=1.0,
            shopping_district="民生社區",
            transport="南京三民站",
        )
        saved = await repo.upsert_from_summary(summary, provider_id="591")
        assert saved.id is not None
        assert saved.name == "鳴森大苑-碧硯閣"
        assert saved.lat == 25.0569
        assert saved.avg_unit_price_wan == 129.0
        assert saved.building_age_years == 1.0
        assert saved.building_type == "住宅大樓"
        assert saved.build_purpose == "住宅"
        assert saved.housing_status == "新成屋"

        # 2. 從 Detail 豐富欄位規格
        detail = NormalizedCommunityDetail(
            provider_id="591",
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            building_type="住宅大樓",
            build_purpose="住家用",
            housing_status="新成屋",
            address="台北市松山區延壽街76之1號",
            region_name="台北市",
            section_name="松山區",
            structure="SRC造",
            total_households=290,
            manage_fee_per_pin=150,
            base_area_pin=450.0,
            public_ratio_pct=32.0,
            facilities=["接待大廳", "空中花園"],
            developer_company="中華工程股份有限公司",
            cover_image_url="https://example.com/cover.jpg",
            park_type_str="平面式",
            park_price="360~420萬",
            land_division="第三之二種住宅區",
            landscape_name="境業設計",
            postulate_name="境業設計",
        )
        updated = await repo.upsert_from_detail(detail, provider_id="591")
        assert updated.id == saved.id
        assert updated.building_type == "住宅大樓"
        assert updated.build_purpose == "住家用"
        assert updated.housing_status == "新成屋"
        assert updated.structure == "SRC造"
        assert updated.total_households == 290
        assert updated.manage_fee_per_pin == 150
        assert updated.facilities == ["接待大廳", "空中花園"]
        assert updated.cover_image_url == "https://example.com/cover.jpg"
        assert updated.park_type_str == "平面式"
        assert updated.park_price == "360~420萬"
        assert updated.base_area_pin == 450.0
        assert updated.land_division == "第三之二種住宅區"
        assert updated.landscape_name == "境業設計"
        assert updated.postulate_name == "境業設計"

        # 3. 搜尋驗證 (含屋齡篩選)
        results = await repo.search(region="台北市", keyword="鳴森", min_age_years=0, max_age_years=5)
        assert len(results) == 1
        assert results[0].name == "鳴森大苑-碧硯閣"

        results_none = await repo.search(min_age_years=10, max_age_years=20)
        assert len(results_none) == 0


@pytest.mark.asyncio
async def test_property_repository_deduplication_and_listings(test_db: DatabaseManager):
    """測試中古屋自動純數值去重合併機制與多平台刊登追蹤"""
    async with test_db.session() as session:
        repo = PropertyRepository(session)

        # 1. 591 來源刊登與物件寫入
        sh_detail = NormalizedSalePropertyDetail(
            provider_id="591",
            external_house_id="20604856",
            title="鳴森大苑景觀高樓3房",
            price_wan=5258,
            unit_price_wan=132.2,
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            total_area_pin=46.29,
            building_type="住宅",
            building_structure="電梯大樓",
            floor_current=2,
            floor_total=24,
            building_age_years=1.0,
            region_name="台北市",
            section_name="松山區",
            address="台北市松山區三民路80巷25號",
            coordinates=GeoPoint(lat=25.0561, lng=121.5645),
            community_name="鳴森大苑-碧硯閣",
        )
        sh_summary_591 = NormalizedSaleListing(
            provider_id="591",
            external_house_id="S20604856",
            title="鳴森大苑景觀高樓3房",
            price_wan=5258,
            unit_price_wan=132.2,
            total_area_pin=46.29,
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            region_name="台北市",
            section_name="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor_current=2,
            floor_total=24,
            cover_image_url="https://img.example.com/cover1.jpg",
        )

        prop1 = await repo.upsert_property_with_listing(
            detail=sh_detail,
            provider_id="591",
            summary=sh_summary_591,
        )
        assert prop1.id is not None
        assert prop1.provider_id == "591"
        assert prop1.external_house_id == "S20604856"
        assert prop1.price_wan == 5258
        assert prop1.floor_current == 2
        assert prop1.rooms == 3
        assert len(prop1.listings) == 1
        assert prop1.listings[0].provider_id == "591"

        # 2. 另一來源 (如信義房屋 sinyi) 刊登同一物理物件 (同社區、同樓層、坪數微幅誤差 46.30 vs 46.29)
        sh_summary_sinyi = NormalizedSaleListing(
            provider_id="sinyi",
            external_house_id="SY_889900",
            title="民生社區鳴森大苑稀有釋出",
            price_wan=5300,
            unit_price_wan=133.0,
            total_area_pin=46.30,  # 誤差在 2% 以內
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            region_name="台北市",
            section_name="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor_current=2,
            cover_image_url="https://img.example.com/cover2.jpg",
        )

        prop2 = await repo.upsert_from_summary(
            summary=sh_summary_sinyi,
            provider_id="sinyi",
            candidate_property_id=prop1.id,
        )

        # 驗證自動合併至同一筆實體，但新增了第二筆刊登
        assert prop2.id == prop1.id
        reloaded = await repo.get_by_id(prop1.id)
        assert reloaded is not None
        assert len(reloaded.listings) == 2

        # 透過信義外部 ID 亦能反查出該標準物件實體
        queried = await repo.get_by_listing("sinyi", "SY_889900")
        assert queried is not None
        assert queried.id == prop1.id

        # 驗證 building_age_years 數值化存取與範圍檢索
        assert reloaded.building_age_years == 1.0
        results_matched = await repo.search(min_age_years=0, max_age_years=5)
        assert len(results_matched) == 1
        assert results_matched[0].id == prop1.id

        results_unmatched = await repo.search(min_age_years=10, max_age_years=20)
        assert len(results_unmatched) == 0


@pytest.mark.asyncio
async def test_property_repository_detached_villa_and_external_community_persistence(test_db: DatabaseManager):
    """測試透天別墅(整棟銷售)與外部社區代碼獨立持久化 (無內部社區時客觀代碼不丟失)"""
    async with test_db.session() as session:
        repo = PropertyRepository(session)

        # 1. 建立透天別墅刊登與詳情 (外部社區 ID 為 5855864，但 communities 表無此社區)
        villa_detail = NormalizedSalePropertyDetail(
            provider_id="591",
            external_house_id="S88776655",
            title="陽明山尊榮透天獨棟別墅",
            price_wan=9800,
            unit_price_wan=98.0,
            total_area_pin=100.0,
            rooms=5,
            living_rooms=3,
            bathrooms=4,
            is_whole_building=True,
            floor_current=None,  # 整棟銷售無單一所在樓層
            floor_total=4,
            building_type="別墅",
            region_name="台北市",
            section_name="士林區",
            external_community_id="5855864",
            community_name="陽明山莊",
        )
        villa_summary = NormalizedSaleListing(
            provider_id="591",
            external_house_id="S88776655",
            title="陽明山尊榮透天獨棟別墅",
            price_wan=9800,
            total_area_pin=100.0,
            rooms=5,
            living_rooms=3,
            bathrooms=4,
            is_whole_building=True,
            floor_current=None,
            floor_total=4,
            region_name="台北市",
            section_name="士林區",
            external_community_id="5855864",
            community_name="陽明山莊",
        )

        saved = await repo.upsert_property_with_listing(
            detail=villa_detail,
            provider_id="591",
            summary=villa_summary,
        )

        # 2. 驗證客觀外部社區代碼 100% 保留，內部 UUID 為 None (因無主檔)
        assert saved.external_community_id == "5855864"
        assert saved.community_uuid == None
        assert saved.community_name == "陽明山莊"
        assert saved.is_whole_building is True
        assert saved.floor_current is None  # 絕不可為 99！
        assert saved.floor_total == 4

        # 3. 驗證依 external_community_id 檢索
        found = await repo.search(external_community_id="5855864")
        assert len(found) == 1
        assert found[0].id == saved.id

        # 4. 驗證整棟透天去重候選者比對
        dup = await repo.find_duplicate_candidate(
            community_name="陽明山莊",
            total_area_pin=100.0,
            rooms=5,
            floor_total=4,
            external_community_id="5855864",
            is_whole_building=True,
        )
        assert dup is not None
        assert dup.id == saved.id


@pytest.mark.asyncio
async def test_new_house_repository_upsert_and_layout_v2(test_db: DatabaseManager):
    """測試新建案 Summary 與 Detail (含結構化 layout_v2) 儲存"""
    async with test_db.session() as session:
        repo = NewHouseRepository(session)

        # 1. 寫入初始 Detail
        nh_detail_init = NormalizedNewHouseDetail(
            provider_id="591",
            external_project_id="138045",
            project_name="長虹MVP",
            build_type="預售屋",
            region_name="台北市",
            section_name="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            min_unit_price_wan=79.0,
            max_unit_price_wan=90.0,
            min_area_pin=28.0,
            max_area_pin=41.0,
            developer_company="長虹建設股份有限公司",
        )
        saved = await repo.upsert_from_detail(nh_detail_init, provider_id="591")
        assert saved.external_project_id == "138045"
        assert saved.min_unit_price_wan == 79.0
        assert saved.max_unit_price_wan == 90.0
        assert saved.min_area_pin == 28.0
        assert saved.max_area_pin == 41.0

        # 2. 豐富完整 Detail
        nh_detail = NormalizedNewHouseDetail(
            provider_id="591",
            external_project_id="138045",
            project_name="長虹MVP",
            build_type="預售屋",
            region_name="台北市",
            section_name="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            manage_fee_per_pin=150,
            structural_engine="SRC鋼骨鋼筋混凝土結構",
            direction_rule="朝西北",
            layouts=[
                NewHouseLayoutSpec(room_name="二房", rooms_count=2, min_area_pin=28.0, max_area_pin=30.0),
                NewHouseLayoutSpec(room_name="三房", rooms_count=3, min_area_pin=35.0, max_area_pin=41.0),
            ],
            min_unit_price_wan=85.0,
            max_unit_price_wan=85.0,
            total_households=290,
            base_area_pin=450.0,
            public_ratio_pct=32.0,
        )
        updated = await repo.upsert_from_detail(nh_detail, provider_id="591")
        assert updated.id == saved.id
        assert updated.manage_fee_per_pin == 150
        assert updated.structural_engine == "SRC鋼骨鋼筋混凝土結構"
        assert isinstance(updated.layouts, list)
        assert len(updated.layouts) == 2
        assert updated.layouts[0]["room_name"] == "二房"
        assert updated.layouts[0]["rooms_count"] == 2
        assert updated.layouts[1]["min_area_pin"] == 35.0

        # 3. 根據外部專案 ID 查詢
        found = await repo.get_by_external_id("591", "138045")
        assert found is not None
        assert found.project_name == "長虹MVP"


@pytest.mark.asyncio
async def test_repository_filter_existing_external_ids(test_db: DatabaseManager):
    """測試三大領域 Repository 的批次外部 ID 快篩功能"""
    async with test_db.session() as session:
        comm_repo = CommunityRepository(session)
        prop_repo = PropertyRepository(session)
        nh_repo = NewHouseRepository(session)

        # 1. 寫入社區資料
        await comm_repo.upsert_from_summary(
            NormalizedCommunitySummary(
                provider_id="591",
                external_community_id="C100",
                community_name="測試社區A",
                region_name="台北市",
                section_name="大安區",
                address="台北市大安區新生南路",
            ),
            provider_id="591",
        )
        existing_comm = await comm_repo.filter_existing_external_ids("591", ["C100", "C101", "C102"])
        assert existing_comm == {"C100"}

        # 2. 寫入中古屋刊登資料
        await prop_repo.upsert_from_summary(
            NormalizedSaleListing(
                provider_id="591",
                external_house_id="S500",
                title="測試房屋A",
                price_wan=3000,
                total_area_pin=35.0,
                region_name="台北市",
                section_name="信義區",
            ),
            provider_id="591",
        )
        existing_prop = await prop_repo.filter_existing_external_ids("591", ["S500", "S501", "S502"])
        assert existing_prop == {"S500"}

        # 3. 寫入新建案資料
        await nh_repo.upsert_from_detail(
            NormalizedNewHouseDetail(
                provider_id="591",
                external_project_id="900",
                project_name="測試建案A",
                build_type="預售屋",
                region_name="台北市",
                section_name="南港區",
                address="台北市南港區重陽路",
            ),
            provider_id="591",
        )
        existing_nh = await nh_repo.filter_existing_external_ids("591", ["900", "901", "902"])
        assert existing_nh == {"900"}
