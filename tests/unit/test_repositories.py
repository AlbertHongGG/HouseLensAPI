"""Unit Tests for HouseLensAPI Storage Repositories & Database Layer"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.common import GeoPoint
from src.domain.community import CommunityDetail, CommunitySummary
from src.domain.new_house import NewHouseDetail, NewHouseLayoutItem, NewHouseSummary
from src.domain.sale_house import SaleHouseDetail, SaleHouseSummary
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
        summary = CommunitySummary(
            community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            build_purpose_simple="住宅",
            building_type_str="新成屋",
            region_name="台北市",
            section_name="松山區",
            full_address="台北市松山區延壽街76之1號",
            coordinates=GeoPoint(lat=25.0569, lng=121.5651),
            avg_unit_price=129.0,
            unit_price_unit="萬/坪",
            living_circle_name="民生社區",
            nearest_station="南京三民站",
        )
        saved = await repo.upsert_from_summary(summary, provider_id="591")
        assert saved.id is not None
        assert saved.name == "鳴森大苑-碧硯閣"
        assert saved.lat == 25.0569

        # 2. 從 Detail 豐富欄位規格
        detail = CommunityDetail(
            community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            build_type_str="新成屋",
            purpose_str="住宅",
            address="台北市松山區延壽街76之1號",
            region_name="台北市",
            section_name="松山區",
            structure="SRC造",
            total_households="290戶",
            management_fee="150元/坪",
            facilities=["接待大廳", "空中花園"],
            developer_company="中華工程股份有限公司",
        )
        updated = await repo.upsert_from_detail(detail, provider_id="591")
        assert updated.id == saved.id  # 確保是同一筆主鍵
        assert updated.structure == "SRC造"
        assert updated.total_households == "290戶"
        assert updated.facilities == ["接待大廳", "空中花園"]

        # 3. 搜尋驗證
        results = await repo.search(region="台北市", keyword="鳴森")
        assert len(results) == 1
        assert results[0].name == "鳴森大苑-碧硯閣"


@pytest.mark.asyncio
async def test_property_repository_deduplication_and_listings(test_db: DatabaseManager):
    """測試中古屋自動去重合併機制與多平台刊登追蹤"""
    async with test_db.session() as session:
        repo = PropertyRepository(session)

        # 1. 591 來源刊登與物件寫入
        sh_detail = SaleHouseDetail(
            house_id="20604856",
            title="鳴森大苑景觀高樓3房",
            price=5258,
            unit_price="132.2萬/坪",
            layout="3房2廳2衛",
            total_area=46.29,
            building_type="住宅",
            building_structure="電梯大樓",
            floor="2F/24F",
            region="台北市",
            section="松山區",
            address="台北市松山區三民路80巷25號",
            lat=25.0561,
            lng=121.5645,
        )
        sh_summary_591 = SaleHouseSummary(
            house_id="S20604856",
            title="鳴森大苑景觀高樓3房",
            price="5,258萬元",
            total_area=46.29,
            layout="3房2廳",
            region="台北市",
            section="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor="2",
            cover_image_url="https://img.example.com/cover1.jpg",
        )

        prop1 = await repo.upsert_property_with_listing(
            detail=sh_detail,
            provider_id="591",
            summary=sh_summary_591,
        )
        assert prop1.id is not None
        assert prop1.price == 5258
        assert len(prop1.listings) == 1
        assert prop1.listings[0].provider_id == "591"

        # 2. 另一來源 (如信義房屋 sinyi) 刊登同一物理物件 (同社區、同樓層、坪數微幅誤差 46.30 vs 46.29)
        sh_summary_sinyi = SaleHouseSummary(
            house_id="SY_889900",
            title="民生社區鳴森大苑稀有釋出",
            price="5,300萬元",
            total_area=46.30,  # 誤差在 2% 以內
            layout="3房2廳",
            region="台北市",
            section="松山區",
            community_name="鳴森大苑-碧硯閣",
            floor="2",
            cover_image_url="https://img.example.com/cover2.jpg",
        )

        prop2 = await repo.upsert_from_summary(
            summary=sh_summary_sinyi,
            provider_id="sinyi",
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


@pytest.mark.asyncio
async def test_new_house_repository_upsert_and_layout_v2(test_db: DatabaseManager):
    """測試新建案 Summary 與 Detail (含結構化 layout_v2) 儲存"""
    async with test_db.session() as session:
        repo = NewHouseRepository(session)

        # 1. 寫入 Summary
        nh_summary = NewHouseSummary(
            source_hid=138045,
            project_name="長虹MVP",
            project_status="預售屋",
            region_name="台北市",
            section_name="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            price="79~90",
            area="28~41坪",
            developer="長虹建設股份有限公司",
        )
        saved = await repo.upsert_from_summary(nh_summary, provider_id="591")
        assert saved.source_hid == 138045
        assert saved.price == "79~90"
        assert saved.area == "28~41坪"

        # 2. 豐富完整 Detail
        nh_detail = NewHouseDetail(
            hid=138045,
            project_name="長虹MVP",
            build_type="預售屋",
            region="台北市",
            section="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            manage_cost="150 元/坪/月",
            structural_engine="SRC鋼骨鋼筋混凝土結構",
            park_planning="平面式111個、機械式41個",
            direction_rule="朝西北",
            build_intro="精工耐震SRC結構",
            park_ratio="1:0.46",
            layout_v2=[
                NewHouseLayoutItem(room="二房", area="28~30"),
                NewHouseLayoutItem(room="三房", area="35~41"),
            ],
            unit_price_str="85 萬/坪",
            parking_price_str="360~420萬",
            total_households="290戶",
        )
        updated = await repo.upsert_from_detail(nh_detail, provider_id="591")
        assert updated.id == saved.id
        assert updated.manage_cost == "150 元/坪/月"
        assert updated.structural_engine == "SRC鋼骨鋼筋混凝土結構"
        assert isinstance(updated.layout_v2, list)
        assert len(updated.layout_v2) == 2
        assert updated.layout_v2[0]["room"] == "二房"
        assert updated.layout_v2[1]["area"] == "35~41"

        # 3. 根據 HID 查詢
        found = await repo.get_by_source_hid("591", 138045)
        assert found is not None
        assert found.project_name == "長虹MVP"
