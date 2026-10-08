"""HouseLensAPI - 信義房屋社區同步與中古屋外鍵補齊整合測試 (Integration Tests)

涵蓋：
1. 信義房屋社區檢索與詳情持久化入庫流程 (Two-Tier SSOT 驗證)
2. 中古屋社區消歧與外鍵補齊服務 (CommunityResolutionService / link-communities) 對接驗證
   - 階段二遠端探索與入庫 (REMOTE_RESOLVED)
   - 階段一本快速對齊 (LOCAL_LINKED)
"""

from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from sqlalchemy import select

from src.core.registry import ProviderRegistry
from src.domain.common import GeoPoint
from src.domain.community import CommunitySearchQuery
from src.domain.enums import Region
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)


from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.provider import SourceSinyiProvider

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
async def test_sinyi_community_search_and_persistence_ssot(
    sync_test_db: DatabaseManager, mock_sinyi_client: AsyncMock
):
    """驗證信義房屋社區清單搜尋、詳情抓取與依 SSOT 劃分入庫 communities 資料表"""
    # 模擬網頁端 /searchCommunity.php 與 /getCommunityContent.php 回應
    async def fake_post_web_api(path: str, payload: dict, **kwargs):
        if path == "/searchCommunity.php":
            return {
                "retCode": "200",
                "retMsg": "成功",
                "content": {
                    "totalCnt": 1,
                    "object": [
                        {
                            "commId": "G0000316",
                            "commName": "帝國花園",
                            "address": "新北市板橋區華江一路１１９號",
                            "latitude": 25.0349905,
                            "longitude": 121.4740942,
                            "uniprice": 72.0,  # 清單均價
                            "age": "3",
                            "image": "https://res.sinyi.com.tw/small.jpg",
                        }
                    ],
                },
            }
        elif path == "/getCommunityContent.php":
            return {
                "retCode": "200",
                "retMsg": "成功",
                "content": {
                    "commId": "G0000316",
                    "name": "帝國花園",
                    "cityName": "新北市",
                    "zipName": "板橋區",
                    "address": "新北市板橋區華江一路１１９號",
                    "age": "3",
                    "houseCount": "1120",
                    "floorRange": "15、19",
                    "publicpercent": "32.00%~36.00%",
                    "publicDesc": "SPA,花園,室內泳池,健身房",
                    "constructCompany": "立信建設",
                    "buildingStructure": "鋼骨,鋼骨鋼筋混凝土",
                    "latitude": 25.0349905,
                    "longitude": 121.4740942,
                    "images": [
                        "https://res.sinyi.com.tw/big1.jpg",
                        "https://res.sinyi.com.tw/big2.jpg",
                    ],
                    "shareURL": "https://sinyi.biz/3pbH7kMmG?openExternalBrowser=1",
                },
            }
        raise ValueError(f"未預期的 API 路徑: {path}")

    mock_sinyi_client.post_web_api.side_effect = fake_post_web_api
    provider = SourceSinyiProvider(client=mock_sinyi_client)

    # 1. 執行社區搜尋
    query = CommunitySearchQuery(
        region_id=Region.NEW_TAIPEI.value,
        section_name="板橋區",
        keywords="帝國花園",
        page=1,
        page_size=10,
    )
    search_res = await provider.community.search_communities(query)


    assert len(search_res.items) == 1
    summary = search_res.items[0]
    assert summary.avg_unit_price_wan == 72.0

    # 2. 抓取完整規格
    detail = await provider.community.get_community_detail(
        summary.external_community_id, summary=summary
    )

    # 3. 寫入資料庫
    async with sync_test_db.session() as session:
        repo = CommunityRepository(session)
        comm_record = await repo.upsert_from_detail(detail, provider_id="sinyi")

    # 4. 嚴格驗證 communities 資料表 38 欄位之 SSOT 入庫精確性
    async with sync_test_db.session() as session:
        stmt = select(CommunityTable).where(
            CommunityTable.provider_id == "sinyi",
            CommunityTable.external_community_id == "G0000316",
        )
        saved = (await session.execute(stmt)).scalar_one()

        # 第一層：清單 API 權威取得
        assert saved.external_community_id == "G0000316"
        assert saved.name == "帝國花園"
        assert saved.address == "新北市板橋區華江一路１１９號"
        assert saved.lat == pytest.approx(25.0349905)
        assert saved.lng == pytest.approx(121.4740942)
        assert saved.avg_unit_price_wan == 72.0
        assert saved.cover_image_url == "https://res.sinyi.com.tw/small.jpg"

        # 第二層：詳情 API 權威取得
        assert saved.region_name == "新北市"
        assert saved.section_name == "板橋區"
        assert saved.building_age_years == 3.0
        assert saved.total_households == 1120
        assert saved.floor_plan == "15、19"
        assert saved.public_ratio_pct == 32.0
        assert saved.structure == "鋼骨,鋼骨鋼筋混凝土"
        assert saved.developer_company == "立信建設"
        assert saved.facilities == ["SPA", "花園", "室內泳池", "健身房"]
        assert saved.image_urls == [
            "https://res.sinyi.com.tw/big1.jpg",
            "https://res.sinyi.com.tw/big2.jpg",
        ]
        assert saved.url == "https://sinyi.biz/3pbH7kMmG?openExternalBrowser=1"

        # 第三類：客觀無資料 100% SQL NULL
        assert saved.building_type is None
        assert saved.purpose is None
        assert saved.housing_status is None
        assert saved.base_area_pin is None
        assert saved.parking_count is None
        assert saved.parking_ratio is None
        assert saved.min_parking_price_wan is None
        assert saved.max_parking_price_wan is None
        assert saved.manage_fee_per_pin is None
        assert saved.shopping_district is None
        assert saved.transport is None
        assert saved.parking_type is None
        assert saved.land_division is None
        assert saved.orientation is None
        assert saved.landscape_designer is None
        assert saved.public_facility_designer is None
        assert saved.builder_company is None
        assert saved.architect_company is None


@pytest.mark.asyncio
async def test_sinyi_link_communities_resolution_flow(
    sync_test_db: DatabaseManager, mock_sinyi_client: AsyncMock
):
    """驗證 CommunityResolutionService 對信義中古屋物件之外鍵補齊與兩階段消歧"""
    async def fake_post_web_api(path: str, payload: dict, **kwargs):
        if path == "/searchCommunity.php":
            return {
                "retCode": "200",
                "content": {
                    "totalCnt": 1,
                    "object": [
                        {
                            "commId": "G0000316",
                            "commName": "帝國花園",
                            "address": "新北市板橋區華江一路１１９號",
                            "latitude": 25.0349905,
                            "longitude": 121.4740942,
                            "uniprice": 72.0,
                            "age": "3",
                            "image": "https://res.sinyi.com.tw/small.jpg",
                        }
                    ],
                },
            }
        elif path == "/getCommunityContent.php":
            return {
                "retCode": "200",
                "content": {
                    "commId": "G0000316",
                    "name": "帝國花園",
                    "cityName": "新北市",
                    "zipName": "板橋區",
                    "address": "新北市板橋區華江一路１１９號",
                    "age": "3",
                    "houseCount": "1120",
                    "floorRange": "15、19",
                    "publicpercent": "32.00%~36.00%",
                    "publicDesc": "SPA,花園",
                    "constructCompany": "立信建設",
                    "buildingStructure": "鋼骨,鋼骨鋼筋混凝土",
                    "images": ["https://res.sinyi.com.tw/big1.jpg"],
                },
            }
        raise ValueError(f"未預期的 API 路徑: {path}")

    mock_sinyi_client.post_web_api.side_effect = fake_post_web_api
    provider = SourceSinyiProvider(client=mock_sinyi_client)

    # 註冊至獨立自帶的測試 Registry
    custom_registry = ProviderRegistry()
    custom_registry.register_instance(provider)


    # 1. 在資料庫建立未關聯社區之信義中古屋物件
    prop_listing = NormalizedSaleListing(
        provider_id="sinyi",
        external_house_id="7342DG",
        title="帝國花園稀有兩房",
        price_wan=2500.0,
        total_area_pin=35.0,
        region_name="新北市",
        section_name="板橋區",
        community_name="帝國花園",
        external_community_id="G0000316",
    )

    async with sync_test_db.session() as session:
        prop_repo = PropertyRepository(session)
        created_prop = await prop_repo.upsert_from_summary(prop_listing, provider_id="sinyi")
        assert created_prop.community_uuid is None  # 尚未扣合外鍵

    # 2. 執行 CommunityResolutionService 補齊任務 (階段二：遠端兩層式探索)
    resolver = CommunityResolutionService(
        provider_registry=custom_registry,
        database=sync_test_db,
    )

    report_1 = await resolver.resolve_unlinked_properties(
        CommunityResolutionOptions(provider_id="sinyi")
    )

    assert report_1.scanned_properties_count == 1
    assert report_1.remotely_resolved_properties_count == 1
    assert report_1.persisted_communities_count == 1
    assert report_1.locally_linked_properties_count == 0

    # 驗證資料庫外鍵已被成功回填，且 communities 表有該實體
    async with sync_test_db.session() as session:
        p_stmt = select(PropertyTable).where(PropertyTable.external_house_id == "7342DG")
        updated_prop = (await session.execute(p_stmt)).scalar_one()
        assert updated_prop.community_uuid is not None


        c_stmt = select(CommunityTable).where(CommunityTable.id == updated_prop.community_uuid)
        linked_comm = (await session.execute(c_stmt)).scalar_one()
        assert linked_comm.external_community_id == "G0000316"
        assert linked_comm.name == "帝國花園"

    # 3. 建立第二間屬於同社區之中古屋，驗證階段一：本地快速對齊 (0 網路請求直接扣合)
    prop_listing_2 = NormalizedSaleListing(
        provider_id="sinyi",
        external_house_id="7343DH",
        title="帝國花園景觀高樓",
        price_wan=3200.0,
        total_area_pin=42.0,
        region_name="新北市",
        section_name="板橋區",
        community_name="帝國花園",
        external_community_id="G0000316",
    )

    async with sync_test_db.session() as session:
        prop_repo = PropertyRepository(session)
        p2 = await prop_repo.upsert_from_summary(prop_listing_2, provider_id="sinyi")
        p2.community_uuid = None
        await session.flush()



    # 重設 client mock，確保本地對齊零網路調用
    mock_sinyi_client.post_web_api.reset_mock()

    report_2 = await resolver.resolve_unlinked_properties(
        CommunityResolutionOptions(provider_id="sinyi")
    )

    assert report_2.scanned_properties_count == 1
    assert report_2.locally_linked_properties_count == 1
    assert report_2.remotely_resolved_properties_count == 0
    assert report_2.persisted_communities_count == 0
    # 驗證 0 網路調用
    mock_sinyi_client.post_web_api.assert_not_called()
