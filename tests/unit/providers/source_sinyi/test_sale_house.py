"""HouseLensAPI - 信義房屋中古屋領域適配器單元測試 (Unit Tests)"""

from unittest.mock import AsyncMock
import pytest

from src.core.exceptions import ResourceNotFoundError
from src.domain.enums import Region
from src.domain.sale_house import SaleHouseSearchQuery
from src.providers.source_sinyi.sale_house import SourceSinyiSaleHouseProvider


@pytest.fixture
def mock_sinyi_client():
    client = AsyncMock()
    return client


@pytest.fixture
def sale_house_provider(mock_sinyi_client):
    return SourceSinyiSaleHouseProvider(client=mock_sinyi_client)


@pytest.mark.asyncio
async def test_search_sale_houses_success(sale_house_provider, mock_sinyi_client):
    # 模擬 /filterObject.php 正常回應
    mock_sinyi_client.post_encrypted.return_value = {
        "retCode": "000000",
        "content": {
            "page": 1,
            "totalCnt": "872",
            "object": [
                {
                    "houseNo": "80689A",
                    "name": "將捷旅境．－真境",
                    "price": 3838,
                    "areaBuilding": 38.19,
                    "layout": "3房2廳2衛",
                    "age": "0.0",
                    "floor": "17",
                    "floors": "22",
                    "address": "台北市文山區木柵路二段",
                    "image": "https://res.sinyi.com.tw/buy/80689A/smallimg/A.JPG",
                    "largeImage": "https://res.sinyi.com.tw/buy/80689A/bigimg/A.JPG",
                    "commId": "",
                    "isParking": False,
                    "parking": "",
                },
                {
                    "houseNo": "9444KH",
                    "name": "敦南開曼景觀戶",
                    "price": 3300,
                    "areaBuilding": 32.82,
                    "layout": "1房1廳1衛",
                    "age": "2.8年",
                    "floor": "1",
                    "floors": "9",
                    "address": "台北市大安區敦化南路二段",
                    "image": "https://res.sinyi.com.tw/buy/9444KH/smallimg/A.JPG",
                    "largeImage": "https://res.sinyi.com.tw/buy/9444KH/bigimg/A.JPG",
                    "commId": "9018853",
                    "isParking": True,
                    "parking": "坡平",
                },
            ],
        },
    }

    query = SaleHouseSearchQuery(
        page=1,
        page_size=20,
        region_id=Region.TAIPEI,
        min_price_wan=3000,
        max_price_wan=4000,
    )

    result = await sale_house_provider.search_sale_houses(query)

    mock_sinyi_client.post_encrypted.assert_called_once()
    args, kwargs = mock_sinyi_client.post_encrypted.call_args
    assert args[0] == "/filterObject.php"
    assert args[1]["filter"]["retType"] == 2
    assert args[1]["filter"]["price"] == {"priceType": 2, "priceRange": ["3000-4000"]}

    assert result.total_records == 872
    assert result.page == 1
    assert result.page_size == 20
    assert len(result.items) == 2
    assert result.has_next is True

    item0 = result.items[0]
    assert item0.provider_id == "sinyi"
    assert item0.external_house_id == "80689A"
    assert item0.title == "將捷旅境．－真境"
    assert item0.price_wan == 3838
    assert item0.total_area_pin == 38.19
    assert item0.floor_current == 17
    assert item0.floor_total == 22
    assert item0.rooms == 3
    assert item0.region_name == "台北市"
    assert item0.section_name == "文山區"
    assert item0.cover_image_url == "https://res.sinyi.com.tw/buy/80689A/bigimg/A.JPG"
    assert item0.url is None

    item1 = result.items[1]
    assert item1.external_house_id == "9444KH"
    assert item1.price_wan == 3300
    assert item1.external_community_id == "9018853"
    assert item1.has_parking is True


@pytest.mark.asyncio
async def test_search_sale_houses_empty_result(sale_house_provider, mock_sinyi_client):
    mock_sinyi_client.post_encrypted.return_value = {
        "retCode": "000000",
        "content": {
            "page": 1,
            "totalCnt": "0",
            "object": [],
        },
    }

    query = SaleHouseSearchQuery(page=1, page_size=20, keywords="無此特定房屋名稱")
    result = await sale_house_provider.search_sale_houses(query)

    assert result.total_records == 0
    assert len(result.items) == 0
    assert result.has_next is False


@pytest.mark.asyncio
async def test_get_sale_house_detail_success(sale_house_provider, mock_sinyi_client):
    # 模擬 /getObjectContent.php 正常回應
    mock_sinyi_client.post_encrypted.return_value = {
        "retCode": "000000",
        "content": {
            "houseNo": "7342DG",
            "name": "敦品苑全新舒適三房車位",
            "price": 3288,
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

    detail = await sale_house_provider.get_sale_house_detail("7342DG")

    mock_sinyi_client.post_encrypted.assert_called_once_with(
        "/getObjectContent.php", {"houseNo": "7342DG", "showOff": 0}
    )

    assert detail.provider_id == "sinyi"
    assert detail.external_house_id == "7342DG"
    assert detail.title == "敦品苑全新舒適三房車位"
    assert detail.price_wan == 3288
    assert detail.unit_price_wan == 87.9
    assert detail.total_area_pin == 37.31
    assert detail.main_area_pin == 18.89
    assert detail.auxiliary_area_pin == 2.01
    assert detail.land_area_pin == 6.52
    assert detail.floor_current == 3
    assert detail.floor_total == 10
    assert detail.rooms == 3
    assert detail.living_rooms == 2
    assert detail.bathrooms == 2
    assert detail.balconies == 1
    assert detail.building_age_years == 0.5
    assert detail.building_type == "華廈"
    assert detail.orientation == "朝南"
    assert detail.region_name == "台北市"
    assert detail.section_name == "大同區"
    assert detail.street == "敦煌路"
    assert detail.external_community_id == "0032408"
    assert detail.community_name == "敦品苑"
    assert detail.cover_image_url == "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG"
    assert len(detail.image_urls) == 3
    assert detail.url == "https://sinyi.biz/3jpKxSbti?openExternalBrowser=1"

    # 100% SQL NULL 斷言
    assert detail.common_area_pin is None
    assert detail.parking_area_pin is None
    assert detail.public_ratio_pct is None
    assert detail.has_lease is None
    assert detail.structure is None
    assert detail.purpose is None
    assert detail.current_state is None


@pytest.mark.asyncio
async def test_get_sale_house_detail_not_found(sale_house_provider, mock_sinyi_client):
    # 模擬查無資料 (content 為空)
    mock_sinyi_client.post_encrypted.return_value = {
        "retCode": "000000",
        "content": {},
    }

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await sale_house_provider.get_sale_house_detail("NON_EXIST_999")

    assert "NON_EXIST_999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_sale_house_detail_empty_id(sale_house_provider):
    with pytest.raises(ResourceNotFoundError):
        await sale_house_provider.get_sale_house_detail("   ")
