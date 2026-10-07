"""HouseLensAPI - 永慶房屋模組數據正規化引擎單元測試套件"""

import pytest

from src.providers.source_yungching.normalizers import (
    clean_str,
    extract_street,
    is_whole_building,
    normalize_region_name,
    parse_car_area,
    parse_facilities,
    parse_floor,
    parse_float,
    parse_int,
    parse_layout,
)


def test_clean_str():
    assert clean_str(None) is None
    assert clean_str("") is None
    assert clean_str("   ") is None
    assert clean_str(" 大安御 ") == "大安御"


def test_parse_float():
    assert parse_float(None) is None
    assert parse_float("") is None
    assert parse_float("43.22") == pytest.approx(43.22)
    assert parse_float(43.22) == pytest.approx(43.22)
    assert parse_float("91.4萬/坪") == pytest.approx(91.4)
    assert parse_float("8.0年") == pytest.approx(8.0)


def test_parse_int():
    assert parse_int(None) is None
    assert parse_int("") is None
    assert parse_int("3,588") == 3588
    assert parse_int(3588) == 3588
    assert parse_int(3588.0) == 3588
    assert parse_int("4354元/月") == 4354


def test_normalize_region_name():
    assert normalize_region_name(None) is None
    assert normalize_region_name("臺北市") == "台北市"
    assert normalize_region_name("台北市") == "台北市"
    assert normalize_region_name("臺中市") == "台中市"


def test_parse_layout():
    assert parse_layout(None) == (None, None, None)
    assert parse_layout("") == (None, None, None)
    assert parse_layout("3房(室)2廳2衛") == (3, 2, 2)
    assert parse_layout("2房1廳1衛") == (2, 1, 1)
    assert parse_layout("4房2廳2.5衛") == (4, 2, 2)


def test_parse_floor():
    assert parse_floor(None) == (None, None)
    assert parse_floor("") == (None, None)
    assert parse_floor("4樓/11樓") == (4, 11)
    assert parse_floor("B1樓/12樓") == (-1, 12)
    assert parse_floor("地下2樓/15樓") == (-2, 15)


def test_parse_car_area():
    assert parse_car_area(None) is None
    assert parse_car_area("") is None
    assert parse_car_area("(含車位3.92坪)") == pytest.approx(3.92)
    assert parse_car_area("車位10.5坪") == pytest.approx(10.5)
    assert parse_car_area("無車位") is None


def test_extract_street():
    assert extract_street(None) is None
    assert extract_street("") is None
    assert extract_street("台北市萬華區和平西路三段") == "和平西路"
    assert extract_street("新北市板橋區文化路一段") == "文化路"


def test_is_whole_building():
    assert is_whole_building(None) is False
    assert is_whole_building("電梯大樓") is False
    assert is_whole_building("透天厝") is True
    assert is_whole_building("別墅") is True
    assert is_whole_building("整棟商辦") is True


def test_parse_facilities():
    assert parse_facilities(None) == []
    raw = "大樓公設完善(健身房、交誼廳、兒童遊戲室、多功能空間、視聽影音室等..)"
    assert parse_facilities(raw) == ["健身房", "交誼廳", "兒童遊戲室", "多功能空間", "視聽影音室"]
