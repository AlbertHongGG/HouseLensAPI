"""HouseLensAPI - 信義房屋社區領域服務提供者單元測試 (Unit Tests for Sinyi Community Provider)"""

from unittest.mock import AsyncMock
import pytest

from src.core.interfaces.community import ICommunityProvider
from src.domain.common import GeoPoint
from src.domain.community import CommunitySearchQuery
from src.domain.enums import Region
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.community import SourceSinyiCommunityProvider
from src.providers.source_sinyi.provider import SourceSinyiProvider


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=SourceSinyiClient)
    return client


@pytest.fixture
def community_provider(mock_client):
    return SourceSinyiCommunityProvider(mock_client)


@pytest.mark.asyncio
async def test_search_communities_success(community_provider, mock_client):
    """測試 search_communities 正常檢索並組裝 PageResult"""
    mock_client.post_web_api.return_value = {
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
                    "uniprice": 72.0,
                    "age": "3",
                    "image": "https://res.sinyi.com.tw/img.jpg",
                }
            ],
        },
    }

    query = CommunitySearchQuery(
        region_id=Region.NEW_TAIPEI.value,
        section_name="板橋區",
        keywords="帝國花園",
        page=1,
        page_size=10,
    )

    page_result = await community_provider.search_communities(query)

    assert page_result.total_records == 1
    assert len(page_result.items) == 1
    item = page_result.items[0]
    assert item.provider_id == "sinyi"
    assert item.external_community_id == "G0000316"
    assert item.community_name == "帝國花園"
    assert item.avg_unit_price_wan == 72.0
    assert item.coordinates == GeoPoint(lat=25.0349905, lng=121.4740942)

    # 驗證傳送之端點
    mock_client.post_web_api.assert_called_once()
    assert mock_client.post_web_api.call_args[0][0] == "/searchCommunity.php"


@pytest.mark.asyncio
async def test_search_communities_direct_id_fallback(community_provider, mock_client):
    """測試關鍵字為 7 碼英數代碼且清單搜尋為 0 時，觸發外部代碼直查兜底防護"""
    # 第一次呼叫 searchCommunity 回傳 0 筆
    # 第二次呼叫 getCommunityContent 回傳詳情內容
    mock_client.post_web_api.side_effect = [
        {"retCode": "200", "content": {"totalCnt": 0, "object": []}},
        {
            "retCode": "200",
            "content": {
                "commId": "G0000316",
                "name": "帝國花園",
                "cityName": "新北市",
                "zipName": "板橋區",
                "address": "新北市板橋區華江一路１１９號",
                "latitude": 25.0349905,
                "longitude": 121.4740942,
                "age": "3",
                "images": ["https://res.sinyi.com.tw/img.jpg"],
            },
        },
    ]

    query = CommunitySearchQuery(keywords="G0000316")
    page_result = await community_provider.search_communities(query)

    assert page_result.total_records == 1
    assert len(page_result.items) == 1
    assert page_result.items[0].external_community_id == "G0000316"
    assert page_result.items[0].community_name == "帝國花園"


@pytest.mark.asyncio
async def test_get_community_detail_success(community_provider, mock_client):
    """測試 get_community_detail 成功調用 /getCommunityContent.php 並轉換為 NormalizedCommunityDetail"""
    mock_client.post_web_api.return_value = {
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
            "publicDesc": "SPA,花園,室內泳池",
            "constructCompany": "立信建設",
            "buildingStructure": "鋼骨,鋼骨鋼筋混凝土",
            "latitude": 25.0349905,
            "longitude": 121.4740942,
            "images": ["https://res.sinyi.com.tw/img1.jpg"],
            "shareURL": "https://sinyi.biz/share",
        },
    }

    detail = await community_provider.get_community_detail("G0000316")

    assert detail.provider_id == "sinyi"
    assert detail.external_community_id == "G0000316"
    assert detail.community_name == "帝國花園"
    assert detail.region_name == "新北市"
    assert detail.section_name == "板橋區"
    assert detail.public_ratio_pct == 32.0
    assert detail.structure == "鋼骨,鋼骨鋼筋混凝土"
    assert detail.developer_company == "立信建設"
    assert detail.total_households == 1120
    assert detail.building_type is None  # 客觀無資料

    mock_client.post_web_api.assert_called_once_with(
        "/getCommunityContent.php", {"commId": "G0000316"}
    )


def test_source_sinyi_provider_community_property():
    """測試頂層 SourceSinyiProvider 正確掛載實作 ICommunityProvider 之實例"""
    provider = SourceSinyiProvider()
    assert isinstance(provider.community, ICommunityProvider)
    assert isinstance(provider.community, SourceSinyiCommunityProvider)
