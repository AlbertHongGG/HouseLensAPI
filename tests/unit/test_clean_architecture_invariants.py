"""Unit Tests for Clean Architecture Invariants and Authoritative Snapshot Overrides

驗證：
1. 領域層 CleanStr 不變量防禦機制：""、"-"、"未提供" 等在實例化瞬間昇華為 None。
2. 倉儲層權威快照覆蓋語意：detail 的 None 能覆蓋並清除舊資料庫髒值。
3. 資料庫欄位收斂：唯存 base_area_pin，零 base_area_num 冗餘。
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.services.deduplication import PropertyDeduplicationService
from src.storage.database import DatabaseManager
from src.storage.models.community import CommunityTable
from src.storage.models.property import PropertyListingTable, PropertyTable
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.property_repo import PropertyRepository


@pytest_asyncio.fixture
async def mem_db():
    """建立非同步記憶體資料庫"""
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


def test_domain_model_clean_str_invariants():
    """驗證 CleanStr 在領域實例化時自動昇華空值與佔位符為 None"""
    # 測試 NormalizedCommunitySummary
    summary = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="C999",
        community_name="測試自衛社區",
        region_name="台北市",
        section_name="大安區",
        address="台北市大安區新生南路",
        building_type="",  # 空字串
        purpose="   ",  # 空白字串
        housing_status="-",  # 破折號佔位符
        shopping_district="未提供",  # 中文佔位符
        transport="暫無資料",  # 佔位符
        cover_image_url="--",  # 雙破折號
    )
    assert summary.building_type is None
    assert summary.purpose is None
    assert summary.housing_status is None
    assert summary.shopping_district is None
    assert summary.transport is None
    assert summary.cover_image_url is None

    # 測試 NormalizedCommunityDetail
    detail = NormalizedCommunityDetail(
        provider_id="591",
        external_community_id="C999",
        community_name="測試自衛社區",
        address="台北市大安區新生南路",
        region_name="台北市",
        section_name="大安區",
        structure="",
        orientation="無",
        floor_plan="-",
        parking_type="",
        land_division="不詳",
        developer_company="未知",
        builder_company="",
        architect_company="",
        landscape_designer="",
        public_facility_designer="",
    )
    assert detail.structure is None
    assert detail.orientation is None
    assert detail.floor_plan is None
    assert detail.parking_type is None
    assert detail.min_parking_price_wan is None
    assert detail.max_parking_price_wan is None
    assert detail.land_division is None
    assert detail.developer_company is None
    assert detail.builder_company is None
    assert detail.architect_company is None
    assert detail.landscape_designer is None
    assert detail.public_facility_designer is None


def test_community_table_schema_convergence():
    """驗證 CommunityTable 徹底收斂至 base_area_pin，不存在 base_area_num"""
    assert hasattr(CommunityTable, "base_area_pin")
    assert not hasattr(CommunityTable, "base_area_num")


@pytest.mark.asyncio
async def test_authoritative_snapshot_override_cleans_dirty_data(mem_db: DatabaseManager):
    """驗證 Detail 快照覆蓋語意：當資料庫存在舊髒資料時，detail 的 None 能權威覆蓋並清空"""
    async with mem_db.session() as session:
        repo = CommunityRepository(session)

        # 1. 建立初始紀錄，包含舊硬體規格與舊文字
        initial_record = CommunityTable(
            id="test-uuid-001",
            provider_id="591",
            external_community_id="C12345",
            name="原始社區名",
            region_name="台北市",
            section_name="大安區",
            address="台北市大安區復興南路",
            avg_unit_price_wan=120.0,
            building_age_years=5.0,
            cover_image_url="https://example.com/summary_cover.jpg",
            # 待清洗的舊硬體規格
            parking_type="舊髒資料_機械式",
            min_parking_price_wan=100.0,
            max_parking_price_wan=150.0,
            land_division="舊分區_住三",
            floor_plan="舊樓層_地上10層",
            structure="舊結構_RC",
            parking_count=50,
            parking_ratio=0.8,
            public_ratio_pct=35.0,
            manage_fee_per_pin=80,
            base_area_pin=300.0,
            developer_company="舊建商",
        )
        session.add(initial_record)
        await session.flush()

        # 2. 準備權威 Detail 快照：
        #    硬體規格中 parking_type, min_parking_price_wan, land_division 等皆為 None (例如國宅無車位型態或無土地分區資料)
        #    avg_unit_price_wan 為 None (detail 未提供均價，需保留 summary 原始均價)
        clean_detail = NormalizedCommunityDetail(
            provider_id="591",
            external_community_id="C12345",
            community_name="原始社區名",
            address="台北市大安區復興南路",
            region_name="台北市",
            section_name="大安區",
            avg_unit_price_wan=None,  # detail 缺失時應 fallback 保留 120.0
            total_households=100,  # 新增規格
            base_area_pin=400.0,  # 權威更新
            public_ratio_pct=33.0,
            parking_count=None,  # 權威清空 (覆蓋 50)
            parking_ratio=None,  # 權威清空 (覆蓋 0.8)
            manage_fee_per_pin=100,
            floor_plan="地上12層",  # 更新
            structure=None,  # 權威清空 (覆蓋 舊結構_RC)
            parking_type=None,  # 權威清空 (覆蓋 舊髒資料_機械式)
            min_parking_price_wan=None,  # 權威清空 (覆蓋 100.0)
            max_parking_price_wan=None,  # 權威清空 (覆蓋 150.0)
            land_division=None,  # 權威清空 (覆蓋 舊分區_住三)
            developer_company=None,  # 權威清空 (覆蓋 舊建商)
            builder_company="新建造商",
        )

        updated = await repo.upsert_from_detail(clean_detail, provider_id="591")

        # 3. 驗證權威覆蓋語意
        # (A) 硬體規格被 None 徹底清空，髒資料不再殘留
        assert updated.parking_type is None
        assert updated.min_parking_price_wan is None
        assert updated.max_parking_price_wan is None
        assert updated.land_division is None
        assert updated.structure is None
        assert updated.parking_count is None
        assert updated.parking_ratio is None
        assert updated.developer_company is None

        # (B) 權威新規格成功寫入
        assert updated.total_households == 100
        assert updated.base_area_pin == 400.0
        assert updated.manage_fee_per_pin == 100
        assert updated.builder_company == "新建造商"
        assert updated.floor_plan == "地上12層"

        # (C) summary 身分與基礎數值成功保留補底
        assert updated.avg_unit_price_wan == 120.0
        assert updated.cover_image_url == "https://example.com/summary_cover.jpg"


@pytest.mark.asyncio
async def test_sale_house_property_authoritative_snapshot_and_fk_linking(mem_db: DatabaseManager):
    """驗證中古屋客觀實體之權威快照覆蓋、統一語言欄位及社區外鍵自動綁定"""
    async with mem_db.session() as session:
        comm_repo = CommunityRepository(session)
        prop_repo = PropertyRepository(session)

        # 1. 預先建立所屬社區實體
        comm_summary = NormalizedCommunitySummary(
            provider_id="591",
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            region_name="台北市",
            section_name="松山區",
            address="台北市松山區三民路80巷",
        )
        saved_comm = await comm_repo.upsert_from_summary(comm_summary, provider_id="591")
        assert saved_comm.id is not None

        # 2. 寫入中古屋刊登與初始實體
        listing_summary = NormalizedSaleListing(
            provider_id="591",
            external_house_id="S20604856",
            title="鳴森大苑景觀高樓3房",
            price_wan=5258,
            total_area_pin=46.29,
            region_name="台北市",
            section_name="松山區",
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            cover_image_url="https://example.com/cover.jpg",
        )
        initial_prop = await prop_repo.upsert_from_summary(listing_summary, provider_id="591")

        # 驗證外部社區代碼持久化與內部 UUID 外鍵自動綁定
        assert initial_prop.community_uuid == saved_comm.id
        assert initial_prop.external_community_id == "5855864"
        assert initial_prop.community_name == "鳴森大苑-碧硯閣"
        assert initial_prop.region_name == "台北市"
        assert initial_prop.section_name == "松山區"

        # 3. 權威詳情快照覆蓋：包含五大產權面積拆解與完整物理規格
        detail_snapshot = NormalizedSalePropertyDetail(
            provider_id="591",
            external_house_id="S20604856",
            title="鳴森大苑景觀高樓3房(權威詳情)",
            price_wan=5258,
            unit_price_wan=132.2,
            total_area_pin=46.29,
            main_area_pin=23.10,
            auxiliary_area_pin=2.78,
            common_area_pin=11.17,
            land_area_pin=5.06,
            parking_area_pin=9.24,
            floor_current=2,
            floor_total=24,
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            balconies=1,
            building_age_years=1.0,
            public_ratio_pct=30.0,
            management_fee_monthly=4200,
            has_lease=False,
            building_type="住宅",
            structure="電梯大樓",
            orientation="坐南朝北",
            purpose="住家用",
            current_state="住宅",
            parking_desc="9.24坪，平面式",
            region_name="台北市",
            section_name="松山區",
            street="三民路",
            address="台北市松山區三民路80巷25號",
            coordinates=GeoPoint(lat=25.056119, lng=121.564513),
            external_community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            cover_image_url="https://example.com/cover.jpg",
        )

        updated_prop = await prop_repo.upsert_property_with_listing(
            detail=detail_snapshot,
            provider_id="591",
            summary=listing_summary,
        )

        # 驗證五大產權面積與規格權威覆蓋
        assert updated_prop.id == initial_prop.id
        assert updated_prop.community_uuid == saved_comm.id
        assert updated_prop.external_community_id == "5855864"
        assert updated_prop.main_area_pin == 23.10
        assert updated_prop.auxiliary_area_pin == 2.78
        assert updated_prop.common_area_pin == 11.17
        assert updated_prop.land_area_pin == 5.06
        assert updated_prop.parking_area_pin == 9.24
        assert updated_prop.building_age_years == 1.0
        assert updated_prop.public_ratio_pct == 30.0
        assert updated_prop.management_fee_monthly == 4200
        assert updated_prop.lat == 25.056119
        assert updated_prop.lng == 121.564513


@pytest.mark.asyncio
async def test_sale_house_multi_level_deduplication(mem_db: DatabaseManager):
    """驗證消歧去重服務：第1級社區比對與第2級無社區物件(公寓/透天)路街樓層比對"""
    dedup = PropertyDeduplicationService(area_tolerance_pct=0.02)

    async with mem_db.session() as session:
        repo = PropertyRepository(session)

        # 1. 建立無社區物件 (老老公寓: 台北市大安區和平東路二段 3F/4F, 30.0坪, 3房)
        apt_summary = NormalizedSaleListing(
            provider_id="provider_a",
            external_house_id="APT_001",
            title="和平東路公寓三樓",
            price_wan=2200,
            total_area_pin=30.0,
            floor_current=3,
            floor_total=4,
            rooms=3,
            region_name="台北市",
            section_name="大安區",
            street="和平東路二段",
            community_name=None,  # 無社區
        )
        saved_apt = await repo.upsert_from_summary(apt_summary, provider_id="provider_a")
        assert saved_apt.id is not None

        # 2. 測試無社區候選物件 (第2級比對命中：同行政區、同路街、同樓層/總樓層、同房數、坪數 29.8坪在 2% 內)
        candidate_same_apt = NormalizedSaleListing(
            provider_id="provider_b",
            external_house_id="APT_002",
            title="大安區和平東路優質三房公寓",
            price_wan=2250,
            total_area_pin=29.8,
            floor_current=3,
            floor_total=4,
            rooms=3,
            region_name="台北市",
            section_name="大安區",
            street="和平東路二段",
            community_name=None,
        )
        res_apt = await dedup.evaluate_candidate(candidate_same_apt, repo)
        assert res_apt.is_duplicate is True
        assert res_apt.matched_property_id == saved_apt.id
        assert res_apt.confidence_score >= 0.7
        assert any("行政區與路街完全相符" in r for r in res_apt.match_reasons)

        # 3. 測試不同樓層 (4F) 不被誤判
        candidate_diff_floor = NormalizedSaleListing(
            provider_id="provider_c",
            external_house_id="APT_003",
            title="和平東路頂樓",
            price_wan=2300,
            total_area_pin=30.0,
            floor_current=4,
            floor_total=4,
            rooms=3,
            region_name="台北市",
            section_name="大安區",
            street="和平東路二段",
            community_name=None,
        )
        res_diff = await dedup.evaluate_candidate(candidate_diff_floor, repo)
        assert res_diff.is_duplicate is False


def test_cross_domain_ssot_two_tier_invariants():
    """驗證跨領域兩層式單一事實來源 (SSOT) 架構不變量：
    - 第一層 (身分與地理空間標識)：100% 統一自清單 API (summary)
    - 第二層 (深層建築規劃與硬體規格)：100% 統一自詳情 API (detail)，零跨 API Fallback 妥協
    """
    from src.providers.source_591.mappers.sale_house_mapper import map_sale_house_detail
    from src.providers.source_591.mappers.new_house_mapper import map_new_house_detail
    from src.providers.source_591.mappers.community_mapper import map_community_detail

    # 1. 中古屋 (Sale House) SSOT 驗證
    sale_summary = NormalizedSaleListing(
        provider_id="591",
        external_house_id="S99887766",
        title="清單專屬權威標題",
        price_wan=1000,
        unit_price_wan=50.0,
        total_area_pin=20.0,
        region_name="台北市",
        section_name="大安區",
        street="信義路",
        address="台北市大安區信義路四段100號",
        external_community_id="C_12345",
        community_name="信義名邸",
        cover_image_url="https://img.example.com/summary_cover.jpg",
    )
    sale_detail_raw = {
        "id": "11223344",  # 詳情原始 ID (應被 summary.external_house_id 覆蓋)
        "kindStr": "電梯大樓",
        "baseInfo": {
            "title": "詳情不一致標題",
            "price": "3500",  # 第二層深層規格：詳情真實成交/委託牌價
            "unitPrice": "70.0",
            "area": "50.0",
            "layout": "3房2廳2衛",
            "info": [
                {"name": "樓層", "value": "10F/20F"},
                {"name": "屋齡", "value": "5年"},
            ],
            "address": {
                "region": "新北市",
                "section": "板橋區",
                "lat": "25.0330",
                "lng": "121.5430",
            },
        },
    }
    mapped_sale = map_sale_house_detail(data=sale_detail_raw, summary=sale_summary)
    # 第一層：100% 統一由 summary 注入
    assert mapped_sale.external_house_id == "S99887766"
    assert mapped_sale.title == "清單專屬權威標題"
    assert mapped_sale.region_name == "台北市"
    assert mapped_sale.section_name == "大安區"
    assert mapped_sale.address == "台北市大安區信義路四段100號"
    assert mapped_sale.external_community_id == "C_12345"
    assert mapped_sale.community_name == "信義名邸"
    assert mapped_sale.cover_image_url == "https://img.example.com/summary_cover.jpg"
    # 第二層：100% 來自詳情 API，絕不取用 summary 之數值
    assert mapped_sale.price_wan == 3500
    assert mapped_sale.unit_price_wan == 70.0
    assert mapped_sale.total_area_pin == 50.0
    assert mapped_sale.floor_current == 10
    assert mapped_sale.floor_total == 20
    assert mapped_sale.rooms == 3
    assert mapped_sale.coordinates is not None
    assert mapped_sale.coordinates.lat == 25.0330

    # 2. 新建案 (New House) SSOT 驗證
    nh_summary = NormalizedNewHouseSummary(
        provider_id="591",
        external_project_id="888001",
        name="清單權威建案名",
        housing_status="預售屋",
        region_name="新北市",
        section_name="三重區",
        address="新北市三重區重新路",
        cover_image_url="https://img.example.com/nh_summary.jpg",
    )
    nh_detail_raw = {
        "housing": {
            "hid": 999999,  # 詳情原始 ID (應被 summary.external_project_id 覆蓋)
            "build_name": "詳情建案名",
            "build_type_name": "成屋",
            "region": "台北市",
            "section": "士林區",
            "price": "60~75",
            "area": "25~45",
            "base_area": "600",
            "households": "150戶",
            "map": {"lat": "25.0600", "lng": "121.4900"},
        }
    }
    mapped_nh = map_new_house_detail(data=nh_detail_raw, summary=nh_summary)
    # 第一層：100% 統一由 summary 注入
    assert mapped_nh.external_project_id == "888001"
    assert mapped_nh.name == "清單權威建案名"
    assert mapped_nh.housing_status == "預售屋"
    assert mapped_nh.region_name == "新北市"
    assert mapped_nh.section_name == "三重區"
    assert mapped_nh.address == "新北市三重區重新路"
    assert mapped_nh.cover_image_url == "https://img.example.com/nh_summary.jpg"
    # 第二層：100% 來自詳情 API
    assert mapped_nh.min_unit_price_wan == 60.0
    assert mapped_nh.max_unit_price_wan == 75.0
    assert mapped_nh.min_area_pin == 25.0
    assert mapped_nh.max_area_pin == 45.0
    assert mapped_nh.base_area_pin == 600.0
    assert mapped_nh.total_households == 150
    assert mapped_nh.lat == 25.0600

    # 3. 社區 (Community) SSOT 驗證
    comm_summary = NormalizedCommunitySummary(
        provider_id="591",
        external_community_id="590011",
        community_name="清單權威社區",
        region_name="台中市",
        section_name="西屯區",
        address="台中市西屯區台灣大道",
        coordinates=GeoPoint(lat=24.1600, lng=120.6400),
        cover_image_url="https://img.example.com/comm_summary.jpg",
    )
    comm_detail_raw = {
        "build_info": {
            "purpose_str": "住宅大樓",
            "purpose_other2": "住家用",
            "build_type": 1,  # 預售屋
            "age": "0年",
            "all_house_num": "200戶",
            "base_area_num": "800坪",
        }
    }
    mapped_comm = map_community_detail(summary=comm_summary, data=comm_detail_raw)
    # 第一層：100% 統一由 summary 注入
    assert mapped_comm.external_community_id == "590011"
    assert mapped_comm.community_name == "清單權威社區"
    assert mapped_comm.region_name == "台中市"
    assert mapped_comm.section_name == "西屯區"
    assert mapped_comm.address == "台中市西屯區台灣大道"
    assert mapped_comm.coordinates is not None
    assert mapped_comm.coordinates.lat == 24.1600
    assert mapped_comm.cover_image_url == "https://img.example.com/comm_summary.jpg"
    # 第二層：100% 來自詳情 API
    assert mapped_comm.building_type == "住宅大樓"
    assert mapped_comm.purpose == "住家用"
    assert mapped_comm.housing_status == "預售屋"
    assert mapped_comm.total_households == 200
    assert mapped_comm.base_area_pin == 800.0
