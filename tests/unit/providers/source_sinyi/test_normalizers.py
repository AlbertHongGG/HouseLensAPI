"""HouseLensAPI - 信義房屋數據正規化與地理防腐層單元測試 (Unit Tests for Normalizers & Geo)"""

import pytest

from src.domain.common import GeoPoint
from src.domain.enums import Region
from src.providers.source_sinyi.geo import (
    ALL_TAIWAN_ZIPCODES,
    TAIWAN_DISTRICT_ZIPCODES,
    resolve_sinyi_zipcodes,
)
from src.providers.source_sinyi.normalizers import (
    clean_str,
    normalize_orientation,
    parse_address,
    parse_age,
    parse_coordinates,
    parse_facilities,
    parse_float,
    parse_floor,
    parse_image_urls,
    parse_int,
    parse_layout,
    parse_management_fee,
    parse_public_ratio,
    parse_unit_price,
)


class TestSinyiGeo:
    """測試信義房屋地理常數與郵遞區號解析"""

    def test_zipcodes_completeness(self):
        assert "台北市" in TAIWAN_DISTRICT_ZIPCODES
        assert "新北市" in TAIWAN_DISTRICT_ZIPCODES
        assert len(ALL_TAIWAN_ZIPCODES) > 300

    def test_resolve_sinyi_zipcodes_city_level(self):
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI)
        assert len(codes) == 12
        assert "100" in codes
        assert "103" in codes

    def test_resolve_sinyi_zipcodes_district_level(self):
        # 精準匹配
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI, section_name="大同區")
        assert codes == ["103"]

        # 模糊匹配
        codes_fuzzy = resolve_sinyi_zipcodes(region_name="台北市", section_name="大安")
        assert codes_fuzzy == ["106"]

    def test_resolve_sinyi_zipcodes_fallback_all_taiwan(self):
        # 未指定縣市且啟用全域回傳
        all_codes = resolve_sinyi_zipcodes(fallback_all_taiwan=True)
        assert len(all_codes) == len(ALL_TAIWAN_ZIPCODES)
        assert all_codes == ALL_TAIWAN_ZIPCODES

        # 未指定縣市且不啟用全域回傳 (預設台北市)
        default_codes = resolve_sinyi_zipcodes(fallback_all_taiwan=False)
        assert len(default_codes) == 12


class TestSinyiNormalizers:
    """測試信義房屋數據正規化純函數庫"""

    def test_clean_str(self):
        assert clean_str("  信義房屋  ") == "信義房屋"
        assert clean_str("") is None
        assert clean_str("   ") is None
        assert clean_str(None) is None

    def test_parse_float(self):
        assert parse_float(25.5) == 25.5
        assert parse_float("25.5") == 25.5
        assert parse_float("8.0年") == 8.0
        assert parse_float("abc") is None
        assert parse_float(None) is None
        assert parse_float(-10) is None

    def test_parse_int(self):
        assert parse_int(100) == 100
        assert parse_int("1,234") == 1234
        assert parse_int(" 567 ") == 567
        assert parse_int("無") is None
        assert parse_int(None) is None

    def test_parse_floor(self):
        assert parse_floor("17") == 17
        assert parse_floor("B1") == -1
        assert parse_floor("b2") == -2
        assert parse_floor("3F") == 3
        assert parse_floor(None) is None

    def test_parse_age(self):
        assert parse_age("0.0") == 0.0
        assert parse_age("1.3年") == 1.3
        assert parse_age("0.5年") == 0.5
        assert parse_age(5) == 5.0
        assert parse_age(None) is None
        assert parse_age("") is None

    def test_parse_unit_price(self):
        assert parse_unit_price("87.90 萬/坪", None) == 87.90
        assert parse_unit_price("本物件含車位，詳洽經紀人員", "88.13 萬") == 88.13
        assert parse_unit_price(None, None) is None

    def test_parse_layout(self):
        assert parse_layout("3房2廳2衛") == (3, 2, 2)
        assert parse_layout("1房1衛") == (1, None, 1)
        assert parse_layout("4房2廳3衛1陽台") == (4, 2, 3)
        assert parse_layout(None) == (None, None, None)

    def test_parse_management_fee(self):
        assert parse_management_fee("每月約 14,095 元(車位管理費另繳納 1,600 元 / 月繳)") == 14095
        assert parse_management_fee("無") is None
        assert parse_management_fee(None) is None

    def test_parse_address(self):
        r, s, st = parse_address("台北市大同區敦煌路")
        assert r == "台北市"
        assert s == "大同區"
        assert st == "敦煌路"

        r2, s2, st2 = parse_address("新北市板橋區華江一路１１９號")
        assert r2 == "新北市"
        assert s2 == "板橋區"
        assert st2 == "華江一路"

        assert parse_address(None) == (None, None, None)

    def test_normalize_orientation(self):
        assert normalize_orientation("南") == "朝南"
        assert normalize_orientation("朝北") == "朝北"
        assert normalize_orientation("坐北朝南") == "坐北朝南"
        assert normalize_orientation("無") is None
        assert normalize_orientation(None) is None

    def test_parse_coordinates(self):
        gp = parse_coordinates(25.0349905, 121.4740942)
        assert gp == GeoPoint(lat=25.0349905, lng=121.4740942)
        # 異常邊界過濾
        assert parse_coordinates(0.0, 0.0) is None
        assert parse_coordinates(None, 121.0) is None

    def test_parse_public_ratio(self):
        assert parse_public_ratio("32.00%~36.00%") == 32.0
        assert parse_public_ratio("30.5%") == 30.5
        assert parse_public_ratio("35") == 35.0
        assert parse_public_ratio(None) is None

    def test_parse_facilities(self):
        raw = "SPA,花園,室內泳池,健身房,KTV、視聽中心"
        res = parse_facilities(raw)
        assert res == ["SPA", "花園", "室內泳池", "健身房", "KTV", "視聽中心"]
        assert parse_facilities(None) == []

    def test_parse_image_urls(self):
        imgs = ["https://a.jpg", "https://b.jpg", "https://a.jpg", "  "]
        res = parse_image_urls(imgs, "https://layout.jpg")
        assert res == ["https://a.jpg", "https://b.jpg", "https://layout.jpg"]
        assert parse_image_urls(None) == []
