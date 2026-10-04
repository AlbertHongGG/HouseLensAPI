"""HouseLensAPI - Source591SaleHouseValidator 單元測試

驗證防腐層對 591 虛擬廣告、定交失效卡片、顯式廣告及真實房源的判定準確性。
"""

import pytest
from src.providers.source_591.mappers.sale_house_validator import Source591SaleHouseValidator


def test_is_virtual_ad_id():
    """驗證 S25 開頭或 25 開頭虛擬廣告 ID 之識別。"""
    # 虛擬廣告卡片 ID
    assert Source591SaleHouseValidator.is_virtual_ad_id("S25209808") is True
    assert Source591SaleHouseValidator.is_virtual_ad_id("s25159303") is True
    assert Source591SaleHouseValidator.is_virtual_ad_id("25209249") is True
    assert Source591SaleHouseValidator.is_virtual_ad_id("S25204734") is True

    # 真實房源 ID
    assert Source591SaleHouseValidator.is_virtual_ad_id("S20856283") is False
    assert Source591SaleHouseValidator.is_virtual_ad_id("20856283") is False
    assert Source591SaleHouseValidator.is_virtual_ad_id("S10999999") is False
    assert Source591SaleHouseValidator.is_virtual_ad_id("10999999") is False

    # 無效與邊界值
    assert Source591SaleHouseValidator.is_virtual_ad_id(None) is False
    assert Source591SaleHouseValidator.is_virtual_ad_id("") is False
    assert Source591SaleHouseValidator.is_virtual_ad_id("25") is False  # 長度小於 8 位


def test_is_deactivated_or_closed():
    """驗證定交下架狀態之識別。"""
    assert Source591SaleHouseValidator.is_deactivated_or_closed({"delivery": "定交"}) is True
    assert Source591SaleHouseValidator.is_deactivated_or_closed({"delivery": " 定交 "}) is True

    # 正常房源無 delivery 或非定交
    assert Source591SaleHouseValidator.is_deactivated_or_closed({}) is False
    assert Source591SaleHouseValidator.is_deactivated_or_closed({"delivery": ""}) is False
    assert Source591SaleHouseValidator.is_deactivated_or_closed({"delivery": "在售"}) is False


def test_is_explicit_ad():
    """驗證顯式廣告 is_ads 之識別。"""
    assert Source591SaleHouseValidator.is_explicit_ad({"is_ads": "1"}) is True
    assert Source591SaleHouseValidator.is_explicit_ad({"is_ads": 1}) is True
    assert Source591SaleHouseValidator.is_explicit_ad({"is_ads": "0"}) is False
    assert Source591SaleHouseValidator.is_explicit_ad({}) is False


def test_is_valid_sale_house_comprehensive():
    """驗證綜合門禁門神判定。"""
    # 1. 正常真實房源
    valid_item = {
        "houseid": "S20856283",
        "title": "奧斯卡談美",
        "kind": "9",
        "kindStr": "住宅",
    }
    assert Source591SaleHouseValidator.is_valid_sale_house(valid_item) is True

    # 2. S25 虛擬廣告卡片 (哪怕無其他廣告標籤)
    s25_item = {
        "houseid": "S25208716",
        "title": "獨家內湖五期【新潤峰哲】",
        "delivery": "定交",
    }
    assert Source591SaleHouseValidator.is_valid_sale_house(s25_item) is False

    # 3. 定交下架卡片 (即使 ID 為普通格式)
    closed_item = {
        "houseid": "S20856283",
        "delivery": "定交",
    }
    assert Source591SaleHouseValidator.is_valid_sale_house(closed_item) is False

    # 4. 顯式廣告卡片
    ad_item = {
        "houseid": "S20856283",
        "is_ads": "1",
    }
    assert Source591SaleHouseValidator.is_valid_sale_house(ad_item) is False

    # 5. 空白或非字典異常項目
    assert Source591SaleHouseValidator.is_valid_sale_house(None) is False
    assert Source591SaleHouseValidator.is_valid_sale_house({}) is False
    assert Source591SaleHouseValidator.is_valid_sale_house({"title": "無 ID 物件"}) is False
