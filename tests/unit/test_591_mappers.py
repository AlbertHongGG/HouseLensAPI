"""Unit Tests for 591 Mappers against Real Captured Data"""

import json
import os
from pathlib import Path
import pytest

from src.domain.community import CommunityDetail, CommunitySummary
from src.domain.new_house import NewHouseDetail, NewHouseSummary
from src.domain.sale_house import SaleHouseDetail, SaleHouseSummary
from src.providers.source_591.mappers.community_mapper import (
    map_community_detail,
    map_community_summary,
)
from src.providers.source_591.mappers.new_house_mapper import (
    map_new_house_detail,
    map_new_house_summary,
)
from src.providers.source_591.mappers.sale_house_mapper import (
    map_sale_house_detail,
    map_sale_house_summary,
)

CAPTURES_DIR = Path(__file__).parent.parent.parent / "封包紀錄"


def load_captured_json(filename: str) -> dict:
    file_path = CAPTURES_DIR / filename
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    idx = content.find("{")
    if idx == -1:
        raise ValueError(f"JSON not found in {filename}")
    return json.loads(content[idx:])


class Test591CommunityMappers:
    def test_map_community_summary_from_capture(self):
        data = load_captured_json("社區清單 Respond.json")
        items = data.get("data", {}).get("items", [])
        assert len(items) > 0

        summary = map_community_summary(items[0])
        assert isinstance(summary, CommunitySummary)
        assert summary.community_id == str(items[0]["id"])
        assert summary.community_name == items[0]["name"]
        assert summary.build_purpose_simple == items[0]["build_purpose_simple"]
        assert summary.region_name == "台北市"
        assert summary.avg_unit_price is not None
        assert summary.coordinates is not None

    def test_map_community_detail_from_capture(self):
        data = load_captured_json("社區詳情資訊 Respond.json")
        data_block = data.get("data", {})
        detail = map_community_detail(data_block)

        assert isinstance(detail, CommunityDetail)
        assert detail.community_id == "5855864"
        assert detail.community_name == "鳴森大苑-碧硯閣"
        assert detail.direction_rule == "朝北、朝南"
        assert detail.park_rate == "1:1.07"
        assert detail.structure == "SRC造"
        assert len(detail.facilities) > 0


class Test591SaleHouseMappers:
    def test_map_sale_house_summary_ads_filtering(self):
        data = load_captured_json("房屋物件清單 Respond.json")
        items = data.get("data", {}).get("items", [])
        assert len(items) > 0

        # Item 0 is an ad item (is_ads == "1")
        assert items[0].get("is_ads") == "1" or items[0].get("is_ads") == 1
        ad_mapped = map_sale_house_summary(items[0])
        assert ad_mapped is None  # Must be filtered out!

        # Item 1 is a real property
        real_mapped = map_sale_house_summary(items[1])
        assert isinstance(real_mapped, SaleHouseSummary)
        assert real_mapped.house_id == "S20604856"
        assert real_mapped.price == "5,258萬元"
        assert real_mapped.total_area == 46.3
        assert real_mapped.layout == "3房2廳"
        assert real_mapped.building_type == "住宅"
        assert real_mapped.has_parking is True
        # Verify no linkman or browse_count
        assert not hasattr(real_mapped, "linkman")
        assert not hasattr(real_mapped, "browse_count")

    def test_map_sale_house_detail_from_capture(self):
        data = load_captured_json("房屋物件詳情資訊 Respond.json")
        data_block = data.get("data", {})
        detail = map_sale_house_detail(data_block)

        assert isinstance(detail, SaleHouseDetail)
        assert detail.house_id == "20604856"
        assert detail.price == 5258
        assert isinstance(detail.price, int)
        assert detail.layout == "3房2廳2衛"
        assert detail.total_area == 46.29
        assert detail.building_type == "住宅"
        assert detail.building_structure == "電梯大樓"

        # 10 specs
        assert detail.floor == "2F/24F"
        assert detail.age == "1年"
        assert detail.orientation == "坐南朝北"
        assert detail.management_fee == "4200元/月"
        assert detail.public_ratio == "30%"
        assert detail.has_lease == "否"

        # Area breakdown
        assert detail.main_building_area == "23.10坪"
        assert detail.auxiliary_area == "2.78坪"
        assert detail.common_area == "11.17坪"
        assert detail.land_area == "5.06坪"
        assert detail.parking_area == "9.24坪"

        # Coordinates
        assert detail.lat == 25.056119
        assert detail.lng == 121.5645131


class Test591NewHouseMappers:
    def test_map_new_house_summary_from_capture(self):
        data = load_captured_json("新建案物件清單 Respond.json")
        items = data.get("data", {}).get("items", [])
        assert len(items) > 0

        summary = map_new_house_summary(items[0])
        assert isinstance(summary, NewHouseSummary)
        assert summary.source_hid == items[0]["hid"]
        assert summary.project_name == items[0]["build_name"]
        assert summary.price == "79~90"
        assert summary.area == "28~41坪"
        assert not hasattr(summary, "price_unit")

    def test_map_new_house_detail_from_capture(self):
        data = load_captured_json("新建案物件詳情資訊 Respond.json")
        data_block = data.get("data", {})
        detail = map_new_house_detail(data_block)

        assert isinstance(detail, NewHouseDetail)
        assert detail.hid == 138045
        assert detail.project_name == "長虹MVP"
        assert detail.region == "台北市"
        assert detail.section == "萬華區"
        assert detail.structural_engine == "SRC鋼骨鋼筋混凝土結構"
        assert len(detail.layout_v2) > 0
        assert detail.layout_v2[0].room == "一房"
        assert detail.layout_v2[0].area == "14~17"
