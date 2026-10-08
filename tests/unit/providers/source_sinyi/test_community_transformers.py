"""HouseLensAPI - 信義房屋社區模型轉換器單元測試 (Unit Tests for Sinyi Community Transformers)"""

import pytest

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_sinyi.community_transformers import (
    map_sinyi_community_detail,
    map_sinyi_community_summary,
    parse_facilities,
    parse_public_ratio,
)


def test_parse_public_ratio():
    """測試公設比字串解析 (取下限數值)"""
    assert parse_public_ratio("32.00%~36.00%") == 32.0
    assert parse_public_ratio("30.5%") == 30.5
    assert parse_public_ratio("35") == 35.0
    assert parse_public_ratio(None) is None
    assert parse_public_ratio("") is None


def test_parse_facilities():
    """測試公共設施字串切分"""
    raw = "SPA,花園,室內泳池,健身房,KTV、視聽中心"
    res = parse_facilities(raw)
    assert res == ["SPA", "花園", "室內泳池", "健身房", "KTV", "視聽中心"]
    assert parse_facilities(None) == []


def test_map_sinyi_community_summary():
    """測試信義房屋清單物件轉換為 NormalizedCommunitySummary"""
    raw_item = {
        "commId": "G0000316",
        "commName": "帝國花園",
        "image": "https://res.sinyi.com.tw/community/0030305/smallimg/A1.JPG",
        "address": "新北市板橋區華江一路１１９號",
        "uniprice": 72.0,
        "age": "3",
        "latitude": 25.0349905,
        "longitude": 121.4740942,
    }

    summary = map_sinyi_community_summary(raw_item)
    assert summary.provider_id == "sinyi"
    assert summary.external_community_id == "G0000316"
    assert summary.community_name == "帝國花園"
    assert summary.address == "新北市板橋區華江一路１１９號"
    assert summary.coordinates == GeoPoint(lat=25.0349905, lng=121.4740942)
    assert summary.avg_unit_price_wan == 72.0
    assert summary.building_age_years == 3.0
    assert summary.cover_image_url == "https://res.sinyi.com.tw/community/0030305/smallimg/A1.JPG"
    assert summary.url == "https://www.sinyi.com.tw/community/G0000316"


def test_map_sinyi_community_detail_with_summary_ssot():
    """測試信義房屋詳情轉換嚴格落實 Two-Tier SSOT 權威劃分"""
    summary = NormalizedCommunitySummary(
        provider_id="sinyi",
        external_community_id="G0000316",
        community_name="帝國花園",
        region_name="",
        section_name="",
        address="新北市板橋區華江一路１１９號",
        coordinates=GeoPoint(lat=25.0349905, lng=121.4740942),
        avg_unit_price_wan=72.0,
        building_age_years=3.0,
        cover_image_url="https://res.sinyi.com.tw/community/0030305/smallimg/A1.JPG",
        url="https://www.sinyi.com.tw/community/G0000316",
        building_type=None,
        purpose=None,
        housing_status=None,
        shopping_district=None,
        transport=None,
    )

    raw_detail = {
        "content": {
            "commId": "G0000316",
            "name": "帝國花園",
            "cityName": "新北市",
            "zipName": "板橋區",
            "address": "新北市板橋區華江一路１１９號",
            "age": "3",
            "floorRange": "15、19",
            "houseCount": "1120",
            "publicpercent": "32.00%~36.00%",
            "publicDesc": "SPA,花園,室內泳池,健身房",
            "constructCompany": "立信建設",
            "buildingStructure": "鋼骨,鋼骨鋼筋混凝土",
            "images": [
                "https://res.sinyi.com.tw/community/0030305/bigimg/A1.JPG",
                "https://res.sinyi.com.tw/community/0030305/bigimg/A2.JPG",
            ],
            "shareURL": "https://sinyi.biz/3pbH7kMmG?openExternalBrowser=1",
        }
    }

    detail = map_sinyi_community_detail(raw_detail, summary=summary)

    # --- 第一層：最小必要資訊 100% 取自 summary ---
    assert detail.provider_id == "sinyi"
    assert detail.external_community_id == "G0000316"
    assert detail.community_name == "帝國花園"
    assert detail.address == "新北市板橋區華江一路１１９號"
    assert detail.coordinates == GeoPoint(lat=25.0349905, lng=121.4740942)
    assert detail.avg_unit_price_wan == 72.0
    assert detail.cover_image_url == "https://res.sinyi.com.tw/community/0030305/smallimg/A1.JPG"

    # --- 第二層：剩下主檔與硬體規格 100% 取自詳情 API ---
    assert detail.region_name == "新北市"
    assert detail.section_name == "板橋區"
    assert detail.building_age_years == 3.0
    assert detail.total_households == 1120
    assert detail.floor_plan == "15、19"
    assert detail.public_ratio_pct == 32.0
    assert detail.structure == "鋼骨,鋼骨鋼筋混凝土"
    assert detail.developer_company == "立信建設"
    assert detail.facilities == ["SPA", "花園", "室內泳池", "健身房"]
    assert len(detail.image_urls) == 2
    assert detail.url == "https://sinyi.biz/3pbH7kMmG?openExternalBrowser=1"

    # --- 第三類：客觀無資料欄位 100% 傳入 None ---
    assert detail.building_type is None
    assert detail.purpose is None
    assert detail.housing_status is None
    assert detail.base_area_pin is None
    assert detail.parking_count is None
    assert detail.parking_ratio is None
    assert detail.min_parking_price_wan is None
    assert detail.max_parking_price_wan is None
    assert detail.manage_fee_per_pin is None
    assert detail.shopping_district is None
    assert detail.transport is None
    assert detail.parking_type is None
    assert detail.land_division is None
    assert detail.orientation is None
    assert detail.landscape_designer is None
    assert detail.public_facility_designer is None
    assert detail.builder_company is None
    assert detail.architect_company is None


def test_map_sinyi_community_detail_without_summary_fallback():
    """測試未提供 summary 時，自動由詳情 API 同名欄位兜底構建最小必要資訊"""
    raw_detail = {
        "content": {
            "commId": "0032408",
            "name": "德運永康",
            "cityName": "台北市",
            "zipName": "大安區",
            "address": "台北市大安區信義路二段",
            "age": "10",
            "latitude": 25.033,
            "longitude": 121.530,
            "houseCount": "50",
            "images": ["https://res.sinyi.com.tw/img1.jpg"],
        }
    }

    detail = map_sinyi_community_detail(raw_detail, summary=None)
    assert detail.external_community_id == "0032408"
    assert detail.community_name == "德運永康"
    assert detail.address == "台北市大安區信義路二段"
    assert detail.coordinates == GeoPoint(lat=25.033, lng=121.530)
    assert detail.region_name == "台北市"
    assert detail.section_name == "大安區"
    assert detail.total_households == 50
    assert detail.avg_unit_price_wan is None  # 詳情 API 客觀無均價
    assert detail.cover_image_url == "https://res.sinyi.com.tw/img1.jpg"
