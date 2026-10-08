"""HouseLensAPI - 信義房屋社區查詢條件建構器單元測試 (Unit Tests for Sinyi Community Query Builder)"""

import pytest

from src.domain.community import CommunitySearchQuery
from src.domain.enums import Region
from src.providers.source_sinyi.geo import ALL_TAIWAN_ZIPCODES
from src.providers.source_sinyi.query_builders import SinyiCommunityQueryBuilder


def test_build_search_payload_default_all_taiwan():
    """測試未指定縣市時，預設涵蓋全台郵遞區號與標準分頁"""
    query = CommunitySearchQuery(keywords="帝國花園", page=1, page_size=20)
    payload = SinyiCommunityQueryBuilder.build_search_payload(query)

    assert payload["page"] == 1
    assert payload["pageCnt"] == 20
    assert payload["sort"] == "0"
    assert payload["isReturnTotal"] is True

    flt = payload["filter"]
    assert flt["retType"] == 2
    assert flt["keyword"] == {"keyword": "帝國花園"}
    assert flt["retRange"] == ALL_TAIWAN_ZIPCODES
    assert "year" not in flt


def test_build_search_payload_specific_city():
    """測試指定特定縣市 (如台北市) 時，retRange 限制為該縣市各區郵遞區號"""
    query = CommunitySearchQuery(region_id=Region.TAIPEI.value, page=2, page_size=15)
    payload = SinyiCommunityQueryBuilder.build_search_payload(query)

    assert payload["page"] == 2
    assert payload["pageCnt"] == 15
    flt = payload["filter"]
    # 台北市郵遞區號應為 100, 103, 104, 105, 106, 108, 110, 111, 112, 114, 115, 116
    assert "100" in flt["retRange"]
    assert "110" in flt["retRange"]
    assert "220" not in flt["retRange"]  # 板橋不應存在


def test_build_search_payload_specific_district():
    """測試指定縣市與行政區 (如新北市板橋區) 時，retRange 鎖定單一郵遞區號"""
    query = CommunitySearchQuery(
        region_id=Region.NEW_TAIPEI.value,
        section_name="板橋區",
        keywords="帝國花園",
    )
    payload = SinyiCommunityQueryBuilder.build_search_payload(query)


    flt = payload["filter"]
    assert flt["retRange"] == ["220"]
    assert flt["keyword"] == {"keyword": "帝國花園"}


def test_build_search_payload_year_filter():
    """測試屋齡區間轉換格式"""
    # 1. 僅有上限
    q1 = CommunitySearchQuery(max_age_years=5.0)
    p1 = SinyiCommunityQueryBuilder.build_search_payload(q1)
    assert p1["filter"]["year"] == "min-5"

    # 2. 僅有下限
    q2 = CommunitySearchQuery(min_age_years=20.0)
    p2 = SinyiCommunityQueryBuilder.build_search_payload(q2)
    assert p2["filter"]["year"] == "20-max"

    # 3. 雙向範圍
    q3 = CommunitySearchQuery(min_age_years=5.0, max_age_years=15.0)
    p3 = SinyiCommunityQueryBuilder.build_search_payload(q3)
    assert p3["filter"]["year"] == "5-15"
