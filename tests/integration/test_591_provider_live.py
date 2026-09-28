"""Integration Tests for 591 Provider with Live Network Calls"""

import pytest

from src.core.registry import registry
from src.domain.common import PageResult
from src.domain.community import CommunityDetail, CommunitySearchQuery, CommunitySummary
from src.domain.new_house import NewHouseDetail, NewHouseSearchQuery, NewHouseSummary
from src.domain.sale_house import SaleHouseDetail, SaleHouseSearchQuery, SaleHouseSummary
from src.providers.source_591.provider import Source591Provider


@pytest.mark.asyncio
async def test_591_health_check():
    provider = registry.get_provider("591")
    assert isinstance(provider, Source591Provider)
    is_healthy = await provider.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_591_community_live_flow():
    provider = registry.get_provider("591")

    # 1. 搜尋台北市社區 (page 1)
    query = CommunitySearchQuery(region_id=1, page=1, page_size=5)
    res = await provider.community.search_communities(query)

    assert isinstance(res, PageResult)
    assert len(res.items) > 0
    first_comm = res.items[0]
    assert isinstance(first_comm, CommunitySummary)
    assert first_comm.community_id is not None
    assert first_comm.community_name != ""

    # 2. 獲取第一筆社區的詳情
    detail = await provider.community.get_community_detail(first_comm.community_id)
    assert isinstance(detail, CommunityDetail)
    assert detail.community_id == first_comm.community_id
    assert detail.community_name != ""


@pytest.mark.asyncio
async def test_591_sale_house_live_flow():
    provider = registry.get_provider("591")

    # 1. 搜尋台北市中古屋 (page 1)
    query = SaleHouseSearchQuery(region_id=1, page=1)
    res = await provider.sale_house.search_sale_houses(query)

    assert isinstance(res, PageResult)
    assert len(res.items) > 0
    first_house = res.items[0]
    assert isinstance(first_house, SaleHouseSummary)
    assert first_house.house_id is not None
    assert first_house.price != ""
    assert first_house.title != ""

    # 2. 獲取該房屋詳情
    detail = await provider.sale_house.get_sale_house_detail(first_house.house_id)
    assert isinstance(detail, SaleHouseDetail)
    assert detail.price > 0
    assert detail.title != ""
    assert detail.region is not None

    # 3. 測試 591 屋齡篩選 (5年以下: _5)
    query_age = SaleHouseSearchQuery(region_id=1, max_age=5, page=1)
    res_age = await provider.sale_house.search_sale_houses(query_age)
    assert len(res_age.items) > 0


@pytest.mark.asyncio
async def test_591_new_house_live_flow():
    provider = registry.get_provider("591")

    # 1. 搜尋新建案
    query = NewHouseSearchQuery(region_id=1, page=1, page_size=5)
    res = await provider.new_house.search_new_houses(query)

    assert isinstance(res, PageResult)
    assert len(res.items) > 0
    first_nh = res.items[0]
    assert isinstance(first_nh, NewHouseSummary)
    assert first_nh.source_hid > 0
    assert first_nh.project_name != ""

    # 2. 獲取建案詳情
    detail = await provider.new_house.get_new_house_detail(str(first_nh.source_hid))
    assert isinstance(detail, NewHouseDetail)
    assert detail.hid == first_nh.source_hid
    assert detail.project_name != ""
    assert detail.region != ""
