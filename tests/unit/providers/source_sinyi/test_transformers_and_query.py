"""HouseLensAPI - 信義房屋查詢構建與資料轉換純函數單元測試 (Unit Tests)"""

import pytest

from src.domain.enums import Region
from src.domain.sale_house import SaleHouseSearchQuery
from src.providers.source_sinyi.query_builder import (
    build_filter_object_payload,
    resolve_sinyi_age_payload,
    resolve_sinyi_price_payload,
    resolve_sinyi_zipcodes,
)
from src.providers.source_sinyi.transformers import (
    normalize_orientation,
    parse_address,
    parse_floor,
    parse_image_urls,
    parse_layout,
    parse_management_fee,
    parse_unit_price,
    transform_sinyi_listing_item,
    transform_sinyi_property_detail,
)


class TestSinyiQueryBuilder:
    """測試信義房屋查詢參數轉換器"""

    def test_resolve_sinyi_zipcodes_city_level(self):
        # 台北市全區 12 區代碼
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI)
        assert len(codes) == 12
        assert "100" in codes
        assert "103" in codes
        assert "116" in codes

    def test_resolve_sinyi_zipcodes_district_level(self):
        # 指定大同區
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI, section_name="大同區")
        assert codes == ["103"]

        # 模糊匹配
        codes_fuzzy = resolve_sinyi_zipcodes(region_name="台北市", section_name="大安")
        assert codes_fuzzy == ["106"]

    def test_resolve_sinyi_price_payload(self):
        # 雙向區間
        p1 = resolve_sinyi_price_payload(min_price_wan=2000, max_price_wan=3000)
        assert p1 == {"priceType": 2, "priceRange": ["2000-3000"]}

        # 單向上限
        p2 = resolve_sinyi_price_payload(max_price_wan=1500)
        assert p2 == {"priceType": 2, "priceRange": ["0-1500"]}

        # 單向下限
        p3 = resolve_sinyi_price_payload(min_price_wan=5000)
        assert p3 == {"priceType": 2, "priceRange": ["5000-99999"]}

        # 無條件
        assert resolve_sinyi_price_payload() is None

    def test_resolve_sinyi_age_payload(self):
        # 小於 5 年
        a1 = resolve_sinyi_age_payload(max_age_years=5.0)
        assert a1 == ["min-5"]

        # 跨區間 3 到 15 年
        a2 = resolve_sinyi_age_payload(min_age_years=3.0, max_age_years=15.0)
        assert a2 == ["min-5", "5-10", "10-20"]

        assert resolve_sinyi_age_payload() is None

    def test_build_filter_object_payload_full(self):
        query = SaleHouseSearchQuery(
            page=2,
            page_size=30,
            region_id=Region.TAIPEI,
            keywords="敦品苑",
            min_price_wan=2500,
            max_price_wan=3500,
            max_age_years=10.0,
            sort_order="price_asc",
        )
        payload = build_filter_object_payload(query)
        assert payload["page"] == 2
        assert payload["pageCnt"] == 30
        assert payload["sort"] == "price-asc"
        f = payload["filter"]
        assert f["retType"] == 2
        assert f["keyword"] == {"keyword": "敦品苑"}
        assert f["price"] == {"priceType": 2, "priceRange": ["2500-3500"]}
        assert f["houseAge"] == ["min-5", "5-10"]
        assert len(f["retRange"]) == 12


class TestSinyiTransformers:
    """測試信義房屋純函數防腐轉換模組"""

    def test_parse_helpers(self):
        # 樓層
        assert parse_floor("17") == 17
        assert parse_floor("B1") == -1
        assert parse_floor("B2") == -2
        assert parse_floor(None) is None

        # 格局
        assert parse_layout("3房2廳2衛") == (3, 2, 2)
        assert parse_layout("1房1衛") == (1, None, 1)
        assert parse_layout(None) == (None, None, None)

        # 單價
        assert parse_unit_price("87.90 萬/坪", None) == 87.9
        assert parse_unit_price("本物件含車位，詳洽經紀人員", "88.13 萬") == 88.13
        assert parse_unit_price(None, None) is None

        # 管理費
        assert parse_management_fee("每月約 14,095 元(車位管理費另繳納 1,600 元 / 月繳)") == 14095
        assert parse_management_fee(None) is None

        # 朝向
        assert normalize_orientation("南") == "朝南"
        assert normalize_orientation("朝北") == "朝北"
        assert normalize_orientation("無") is None

        # 地址拆解
        r, s, st = parse_address("台北市大同區敦煌路")
        assert r == "台北市"
        assert s == "大同區"
        assert st == "敦煌路"

        # 圖片去重
        imgs = ["https://a.jpg", "https://b.jpg", "https://a.jpg"]
        res = parse_image_urls(imgs, "https://layout.jpg")
        assert res == ["https://a.jpg", "https://b.jpg", "https://layout.jpg"]

    def test_transform_sinyi_listing_item(self):
        sample_obj = {
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
        }
        listing = transform_sinyi_listing_item(sample_obj)
        assert listing.provider_id == "sinyi"
        assert listing.external_house_id == "80689A"
        assert listing.title == "將捷旅境．－真境"
        assert listing.price_wan == 3838
        assert listing.total_area_pin == 38.19
        assert listing.floor_current == 17
        assert listing.floor_total == 22
        assert listing.rooms == 3
        assert listing.living_rooms == 2
        assert listing.bathrooms == 2
        assert listing.building_age_years == 0.0
        assert listing.region_name == "台北市"
        assert listing.section_name == "文山區"
        assert listing.street == "木柵路二段"
        assert listing.external_community_id is None
        assert listing.community_name is None
        assert listing.cover_image_url == "https://res.sinyi.com.tw/buy/80689A/bigimg/A.JPG"
        # 清單未提供官方展示網址，固定為 None，由詳情提供
        assert listing.url is None

    def test_transform_sinyi_property_detail(self):
        sample_content = {
            "houseNo": "7342DG",
            "name": "敦品苑全新舒適三房車位",
            "price": 3288,
            "price_item": "87.90 萬/坪",
            "rawUniPrice": "88.13 萬",
            "address": "台北市大同區敦煌路",
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
            "images": [
                "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG",
                "https://res.sinyi.com.tw/buy/7342DG/bigimg/B.JPG",
            ],
        }
        detail = transform_sinyi_property_detail(sample_content)
        assert detail.provider_id == "sinyi"
        assert detail.external_house_id == "7342DG"
        assert detail.title == "敦品苑全新舒適三房車位"
        assert detail.price_wan == 3288
        assert detail.unit_price_wan == 87.9
        assert detail.total_area_pin == 37.31
        assert detail.main_area_pin == 18.89
        # 附屬建物 = 20.9 - 18.89 = 2.01
        assert detail.auxiliary_area_pin == 2.01
        assert detail.balconies == 1
        assert detail.land_area_pin == 6.52
        # 鐵律：客觀無資料 100% SQL NULL
        assert detail.common_area_pin is None
        assert detail.parking_area_pin is None
        assert detail.public_ratio_pct is None
        assert detail.has_lease is None
        assert detail.structure is None
        assert detail.purpose is None
        assert detail.current_state is None

        # 規格
        assert detail.floor_current == 3
        assert detail.floor_total == 10
        assert detail.rooms == 3
        assert detail.living_rooms == 2
        assert detail.bathrooms == 2
        assert detail.building_age_years == 0.5
        assert detail.management_fee_monthly == 3500
        assert detail.building_type == "華廈"
        assert detail.is_whole_building is False
        assert detail.orientation == "朝南"
        assert detail.parking_desc == "1個塔式車位(車位總價：200萬)"
        assert detail.region_name == "台北市"
        assert detail.section_name == "大同區"
        assert detail.street == "敦煌路"
        assert detail.external_community_id == "0032408"
        assert detail.community_name == "敦品苑"
        assert detail.coordinates is not None
        assert detail.coordinates.lat == 25.076032
        assert detail.coordinates.lng == 121.51642
        assert detail.cover_image_url == "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG"
        assert detail.image_urls == [
            "https://res.sinyi.com.tw/buy/7342DG/bigimg/A.JPG",
            "https://res.sinyi.com.tw/buy/7342DG/bigimg/B.JPG",
            "https://res.sinyi.com.tw/buy/7342DG/bigimg/E.JPG",
        ]
        assert detail.url == "https://sinyi.biz/3jpKxSbti?openExternalBrowser=1"
