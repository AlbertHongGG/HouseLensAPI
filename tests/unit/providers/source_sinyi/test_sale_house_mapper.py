"""HouseLensAPI - 信義房屋中古屋模型映射器單元測試 (Unit Tests for Sale House Mapper)"""

import pytest

from src.providers.source_sinyi.mappers import (
    map_sinyi_sale_house_detail,
    map_sinyi_sale_house_list_item,
)


class TestSinyiSaleHouseMapper:
    """測試信義房屋中古屋模型裝配器"""

    def test_map_sinyi_sale_house_list_item(self):
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
        listing = map_sinyi_sale_house_list_item(sample_obj)
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
        assert listing.url is None

    def test_map_sinyi_sale_house_detail(self):
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
        detail = map_sinyi_sale_house_detail(sample_content)
        assert detail.provider_id == "sinyi"
        assert detail.external_house_id == "7342DG"
        assert detail.title == "敦品苑全新舒適三房車位"
        assert detail.price_wan == 3288
        assert detail.unit_price_wan == 87.9
        assert detail.total_area_pin == 37.31
        assert detail.main_area_pin == 18.89
        assert detail.auxiliary_area_pin == 2.01
        assert detail.balconies == 1
        assert detail.land_area_pin == 6.52
        assert detail.common_area_pin is None
        assert detail.parking_area_pin is None
        assert detail.public_ratio_pct is None
        assert detail.has_lease is None
        assert detail.structure is None
        assert detail.purpose is None
        assert detail.current_state is None
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
