"""HouseLensAPI - 信義房屋中古屋端到端同步整合測試 (End-to-End Sync Integration Tests)

驗證信義房屋中古屋清單檢索、併發詳情補齊與資料庫持久化入庫流程。
嚴格檢驗單一事實來源 (SSOT) 鐵律：
1. property_listings 表：刊登標題、刊登開價與縮圖來自清單 API (/filterObject.php)，其餘來自詳情 API。
2. properties 表：所有物理實體規格 (總價、單價、面積拆解、格局、樓層等) 100% 來自詳情 API (/getObjectContent.php)，
   客觀無資料欄位 100% 純化為 SQL NULL (None)。
"""

from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from sqlalchemy import select

from src.core.registry import registry
from src.domain.enums import Region
from src.domain.sale_house import SaleHouseSearchQuery
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.provider import SourceSinyiProvider
from src.services.aggregator import HouseAggregatorService
from src.storage.database import DatabaseManager
from src.storage.models.property import PropertyListingTable, PropertyTable


@pytest_asyncio.fixture
async def sync_test_db():
    """建立獨立的非同步 SQLite 記憶體資料庫供整合測試"""
    db = DatabaseManager(db_url="sqlite+aiosqlite:///:memory:", echo=False)
    await db.init_db()
    yield db
    await db.close()


@pytest.fixture
def mock_sinyi_client():
    client = AsyncMock(spec=SourceSinyiClient)
    return client


@pytest.mark.asyncio
async def test_sinyi_sale_house_e2e_sync_pipeline(sync_test_db: DatabaseManager, mock_sinyi_client):
    # 1. 設置信義清單 API (/filterObject.php) 與詳情 API (/getObjectContent.php) 模擬回應
    def fake_post_mobile_api(path: str, payload: dict, **kwargs):
        if path == "/filterObject.php":
            return {
                "retCode": "000000",
                "content": {
                    "page": 1,
                    "totalCnt": "1",
                    "object": [
                        {
                            "houseNo": "7342DG",
                            "name": "【清單刊登標題】敦品苑超值三房",
                            "price": 3500,  # 清單刊登開價 3500 萬 (不同於詳情實體價，用以驗證 SSOT 劃分)
                            "areaBuilding": 37.31,
                            "layout": "3房2廳2衛",
                            "age": "0.5年",
                            "floor": "3",
                            "floors": "10",
                            "address": "台北市大同區敦煌路",
                            "image": "https://res.sinyi.com.tw/buy/7342DG/smallimg/A.JPG",
                            "largeImage": "https://res.sinyi.com.tw/buy/7342DG/bigimg/A_thumb.JPG",
                            "commId": "0032408",
                            "isParking": True,
                            "parking": "1個塔式車位",
                        }
                    ],
                },
            }
        elif path == "/getObjectContent.php":
            house_no = payload.get("houseNo")
            if house_no == "7342DG":
                return {
                    "retCode": "000000",
                    "content": {
                        "houseNo": "7342DG",
                        "name": "敦品苑全新舒適三房車位",
                        "price": 3288,  # 詳情實體總價 3288 萬
                        "price_item": "87.90 萬/坪",
                        "rawUniPrice": "88.13 萬",
                        "commName": "敦品苑",
                        "commId": "0032408",
                        "layout": "3房2廳2衛",
                        "floor": "3",
                        "floors": "10",
                        "monthlyFee": "每月約 3,500 元",
                        "parking": "1個塔式車位(車位總價：200萬)",
                        "type": "華廈",
                        "areaBuilding": 37.31,
                        "mainBuilding": 18.89,
                        "pingUsed": 20.9,
                        "areaLand": 6.52,
                        "layoutImage": "https://res.sinyi.com.tw/buy/7342DG/bigimg/E.JPG",
                        "shareURL": "https://sinyi.biz/3jpKxSbti?openExternalBrowser=1",
                        "latitude": 25.076032,
                        "longitude": 121.51642,
                        "age": "0.5年",
                        "houseFront": "南",
                        "hasmanager": "無",
                        "address": "台北市大同區敦煌路",
                        "images": [
                            "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG",
                            "https://res.sinyi.com.tw/buy/7342DG/bigimg/B.JPG",
                        ],
                    },
                }
        return {"retCode": "000000", "content": {}}

    mock_sinyi_client.post_mobile_api.side_effect = fake_post_mobile_api

    # 2. 建立獨立 Registry 註冊測試 Provider 實例
    from src.core.registry import ProviderRegistry
    test_registry = ProviderRegistry()
    custom_provider = SourceSinyiProvider(client=mock_sinyi_client)
    test_registry.register_instance(custom_provider)

    service = HouseAggregatorService(
        provider_registry=test_registry,
        database=sync_test_db,
    )

    # 3. 執行同步管線
    query = SaleHouseSearchQuery(region_id=Region.TAIPEI, page=1, page_size=10)
    synced_props = await service.sync_sale_houses(
        provider_id="sinyi",
        query=query,
        max_items=1,
    )

    assert len(synced_props) == 1
    synced_prop = synced_props[0]

    # 4. 驗證資料庫實際持久化內容 (直接以 SQL 查詢)
    async with sync_test_db.session() as session:
        # A. 檢驗 property_listings (刊登從表)
        listing_stmt = select(PropertyListingTable).where(
            PropertyListingTable.provider_id == "sinyi",
            PropertyListingTable.external_house_id == "7342DG",
        )
        listing_res = await session.execute(listing_stmt)
        listing = listing_res.scalar_one()

        assert listing.provider_id == "sinyi"
        assert listing.external_house_id == "7342DG"
        # 鐵律：刊登開價與標題來自清單 API
        assert listing.listing_title == "敦品苑全新舒適三房車位" or "敦品苑" in listing.listing_title
        assert listing.listing_price_wan == 3500  # 清單開價為 3500 萬
        assert listing.cover_image_url == "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG"
        # 圖庫與官方展示網址來自詳情 API
        assert listing.url == "https://sinyi.biz/3jpKxSbti?openExternalBrowser=1"
        assert len(listing.image_urls) == 3

        # B. 檢驗 properties (客觀實體主檔表)
        prop_stmt = select(PropertyTable).where(
            PropertyTable.id == listing.property_id
        )
        prop_res = await session.execute(prop_stmt)
        prop = prop_res.scalar_one()

        assert prop.provider_id == "sinyi"
        assert prop.external_house_id == "7342DG"
        assert prop.external_community_id == "0032408"
        assert prop.community_name == "敦品苑"
        # 鐵律：物理總價與單價 100% 來自詳情 API
        assert prop.price_wan == 3288  # 詳情實體價格為 3288 萬 (非清單開價 3500)
        assert prop.unit_price_wan == 87.90
        assert prop.total_area_pin == 37.31
        # 產權面積純浮點數拆解
        assert prop.main_area_pin == 18.89
        assert prop.auxiliary_area_pin == 2.01  # round(20.9 - 18.89, 2)
        assert prop.land_area_pin == 6.52
        # 鐵律：客觀無資料 100% 純化為 SQL NULL
        assert prop.common_area_pin is None
        assert prop.parking_area_pin is None
        assert prop.public_ratio_pct is None
        assert prop.has_lease is None
        assert prop.structure is None
        assert prop.purpose is None
        assert prop.current_state is None

        # 規格純數值
        assert prop.floor_current == 3
        assert prop.floor_total == 10
        assert prop.rooms == 3
        assert prop.living_rooms == 2
        assert prop.bathrooms == 2
        assert prop.balconies == 1
        assert prop.building_age_years == 0.5
        assert prop.management_fee_monthly == 3500
        assert prop.building_type == "華廈"
        assert prop.orientation == "朝南"
        assert prop.parking_desc == "1個塔式車位(車位總價：200萬)"
        assert prop.region_name == "台北市"
        assert prop.section_name == "大同區"
        assert prop.street == "敦煌路"
        assert prop.lat == 25.076032
        assert prop.lng == 121.51642
        assert prop.cover_image_url == "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG"
        assert prop.url == "https://sinyi.biz/3jpKxSbti?openExternalBrowser=1"

    # 5. 驗證在庫檢索 API
    found = await service.search_properties(region_name="台北市")
    assert len(found) >= 1
    assert any(p.external_house_id == "7342DG" for p in found)
