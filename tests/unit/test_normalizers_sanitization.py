"""單元測試 - 591 數據清洗與字串空值純化引擎測試 (Normalizers Sanitization Tests)"""

from src.providers.source_591.normalizers import (
    clean_optional_str,
    clean_parking_count,
    parse_parking_price_range,
)


class TestCleanOptionalStr:
    """測試 clean_optional_str 字串清洗與空值純化"""

    def test_none_and_empty_returns_none(self):
        assert clean_optional_str(None) is None
        assert clean_optional_str("") is None
        assert clean_optional_str("   ") is None

    def test_invalid_placeholders_returns_none(self):
        assert clean_optional_str("-") is None
        assert clean_optional_str("--") is None
        assert clean_optional_str("---") is None
        assert clean_optional_str("無") is None
        assert clean_optional_str("暫無") is None
        assert clean_optional_str("未提供") is None
        assert clean_optional_str("待定") is None
        assert clean_optional_str("價格待定") is None
        assert clean_optional_str("None") is None
        assert clean_optional_str("null") is None
        assert clean_optional_str("NULL") is None

    def test_valid_strings_stripped_and_preserved(self):
        assert clean_optional_str("住宅大樓") == "住宅大樓"
        assert clean_optional_str("  平面式  ") == "平面式"
        assert clean_optional_str("第三種住宅區") == "第三種住宅區"
        assert clean_optional_str("RC造") == "RC造"


class TestParseParkingPriceRange:
    """測試 parse_parking_price_range 車位價格純數值解析與 591 統計 Bug 修復"""

    def test_empty_or_none(self):
        assert parse_parking_price_range(None) == (None, None)
        assert parse_parking_price_range("") == (None, None)
        assert parse_parking_price_range("   ") == (None, None)
        assert parse_parking_price_range("-") == (None, None)
        assert parse_parking_price_range({"price": "", "unit": "萬"}) == (None, None)
        assert parse_parking_price_range({"price": None, "unit": "萬"}) == (None, None)
        assert parse_parking_price_range({"pending": 1, "price": "價格待定"}) == (None, None)

    def test_zero_to_max_bug_fixed_to_highest(self):
        # 591 實價登錄將無車位 0 元納入區間的 Bug 修復 (包含半形與全形符號 ~ ～ - －)
        assert parse_parking_price_range("0~320萬") == (None, 320.0)
        assert parse_parking_price_range("0～320萬") == (None, 320.0)
        assert parse_parking_price_range("0－320萬") == (None, 320.0)
        assert parse_parking_price_range("0~320") == (None, 320.0)
        assert parse_parking_price_range({"price": "0~320", "unit": "萬"}) == (None, 320.0)
        assert parse_parking_price_range({"price": "0～320", "unit": "萬"}) == (None, 320.0)
        assert parse_parking_price_range("0~2,750萬") == (None, 2750.0)
        assert parse_parking_price_range("0～2,750萬") == (None, 2750.0)
        assert parse_parking_price_range("0-500萬") == (None, 500.0)
        assert parse_parking_price_range("0~1,120萬") == (None, 1120.0)
        assert parse_parking_price_range("最高 250萬") == (None, 250.0)

    def test_standard_range_preserved(self):
        assert parse_parking_price_range("290~330萬") == (290.0, 330.0)
        assert parse_parking_price_range("290～330萬") == (290.0, 330.0)
        assert parse_parking_price_range({"price": "290~330", "unit": "萬"}) == (290.0, 330.0)
        assert parse_parking_price_range("220-300萬") == (220.0, 300.0)
        assert parse_parking_price_range("360~500萬") == (360.0, 500.0)
        assert parse_parking_price_range({"price": "155~320", "unit": "萬"}) == (155.0, 320.0)

    def test_single_price_preserved(self):
        assert parse_parking_price_range("350萬") == (350.0, 350.0)
        assert parse_parking_price_range({"price": "350", "unit": "萬"}) == (350.0, 350.0)
        assert parse_parking_price_range("260") == (260.0, 260.0)



class TestCleanParkingCount:
    """測試 clean_parking_count 社區車位總數純整數與未登錄語意判定"""

    def test_positive_counts(self):
        assert clean_parking_count(68, "平面式68個", "1:1.03") == 68
        assert clean_parking_count("152", None, None) == 152
        assert clean_parking_count(442) == 442

    def test_zero_without_details_returns_none(self):
        # 健安新城模式: 591 回傳 0 且無車位描述與配比 -> 代表未登錄/待查
        assert clean_parking_count(0, "", "") is None
        assert clean_parking_count("0", None, None) is None
        assert clean_parking_count(0, "-", "-") is None

    def test_explicit_no_parking_returns_zero(self):
        # 明確載明無車位
        assert clean_parking_count(0, "無車位", None) == 0
        assert clean_parking_count(0, "本社區無車位規劃", None) == 0

    def test_none_or_invalid(self):
        assert clean_parking_count(None) is None
        assert clean_parking_count("") is None
        assert clean_parking_count("待定") is None
