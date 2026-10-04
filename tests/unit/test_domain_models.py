"""Unit Tests for HouseLensAPI Canonical Domain Models"""

import pytest
from pydantic import ValidationError

from src.domain.enums import Region, BuildingType, NewHouseStatus, AgeRange
from src.domain.common import GeoPoint, StructuredAddress, PageResult
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
    CommunitySearchQuery,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.domain.new_house import (
    NewHouseLayoutSpec,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
    NewHouseSearchQuery,
)


class TestEnums:
    def test_region_enum(self):
        assert Region.TAIPEI == 1
        assert Region.NEW_TAIPEI == 3
        assert Region.from_name("台北市") == Region.TAIPEI
        assert Region.from_name("臺中市") == Region.TAICHUNG
        with pytest.raises(ValueError):
            Region.from_name("不存在的城市")

    def test_building_type_enum(self):
        assert BuildingType.RESIDENTIAL == "住宅"
        assert BuildingType.ELEVATOR_BUILDING == "電梯大樓"

    def test_new_house_status(self):
        assert NewHouseStatus.PRE_SALE == "預售屋"
        assert NewHouseStatus.NEW_CONSTRUCTION == "新成屋"


class TestCommonModels:
    def test_geo_point(self):
        pt = GeoPoint(lat=25.0561, lng=121.5645)
        assert pt.lat == 25.0561
        assert pt.lng == 121.5645

    def test_structured_address(self):
        addr = StructuredAddress(
            region="台北市",
            section="松山區",
            street="三民路",
            lane="80巷",
            number="25號",
            full_address="台北市松山區三民路80巷25號",
            coordinates=GeoPoint(lat=25.0561, lng=121.5645),
        )
        assert addr.region == "台北市"
        assert addr.coordinates.lat == 25.0561

    def test_page_result(self):
        res = PageResult.create(items=[1, 2, 3], total_records=10, page=1, page_size=3)
        assert res.has_next is True
        assert res.total_records == 10

        res_last = PageResult.create(items=[1, 2, 3], total_records=3, page=1, page_size=3)
        assert res_last.has_next is False


class TestCommunityModels:
    def test_community_summary_instantiation(self):
        summary = NormalizedCommunitySummary(
            community_id="5934204",
            community_name="鳴森大苑-鳴森苑",
            region_name="台北市",
            section_name="松山區",
            full_address="台北市松山區延壽街72巷...",
            coordinates=GeoPoint(lat=25.056, lng=121.564),
            avg_unit_price_wan=141.0,
            building_age_years=1.0,
            building_type="住宅大樓",
            build_purpose="住宅",
            housing_status="新成屋",
            living_circle_name="民生社區",
            nearest_station="南京三民站",
            cover_image_url="https://example.com/cover.jpg",
        )
        assert summary.community_id == "5934204"
        assert summary.avg_unit_price_wan == 141.0
        assert summary.coordinates.lat == 25.056
        assert summary.address == "台北市松山區延壽街72巷..."
        assert summary.housing_status == "新成屋"
        assert summary.building_type == "住宅大樓"

    def test_community_detail_instantiation(self):
        detail = NormalizedCommunityDetail(
            community_id="5934204",
            community_name="鳴森大苑-鳴森苑",
            address="台北市松山區延壽街72巷",
            region_name="台北市",
            section_name="松山區",
            building_type="住宅大樓",
            build_purpose="住家用",
            housing_status="新成屋",
            parking_ratio_pct=1.07,
            direction_rule="朝北、朝南",
            facilities=["接待大廳", "空中花園"],
            manage_fee_per_pin=150,
            total_households=290,
            base_area_num=450.0,
            public_ratio_pct=32.0,
        )
        assert detail.community_id == "5934204"
        assert len(detail.facilities) == 2
        assert detail.direction_rule == "朝北、朝南"
        assert detail.manage_fee_per_pin == 150
        assert detail.building_type == "住宅大樓"
        assert detail.build_purpose == "住家用"
        assert detail.housing_status == "新成屋"


class TestSaleHouseModels:
    def test_sale_house_summary_clean_contract(self):
        summary = NormalizedSaleListing(
            provider_id="591",
            external_house_id="S20604856",
            title="全新碧硯閣三房車位",
            price_wan=5258,
            unit_price_wan=132.2,
            total_area_pin=46.3,
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            building_type="住宅",
            region="台北市",
            section="松山區",
            street="三民路",
            address="鳴森大苑-碧硯閣 松山區-三民路",
            community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            floor_current=2,
            floor_total=24,
            has_parking=True,
            cover_image_url="https://example.com/house.jpg",
        )
        assert summary.house_id == "S20604856"
        assert summary.total_area_pin == 46.3
        assert summary.price_wan == 5258
        assert summary.has_parking is True
        assert not hasattr(summary, "linkman")
        assert not hasattr(summary, "browse_count")

    def test_sale_house_detail_cross_platform_contract(self):
        detail = NormalizedSalePropertyDetail(
            external_house_id="20604856",
            title="全新碧硯閣三房車位",
            price_wan=5258,
            unit_price_wan=132.2,
            rooms=3,
            living_rooms=2,
            bathrooms=2,
            balconies=1,
            total_area_pin=46.29,
            building_type="住宅",
            building_structure="電梯大樓",
            floor_current=2,
            floor_total=24,
            building_age_years=1.0,
            orientation="坐南朝北",
            management_fee_monthly=4200,
            public_ratio_pct=30.0,
            has_lease=False,
            parking_desc="9.24坪，平面式，已含售金內",
            main_area_pin=23.10,
            auxiliary_area_pin=2.78,
            common_area_pin=11.17,
            land_area_pin=5.06,
            parking_area_pin=9.24,
            region="台北市",
            section="松山區",
            street="三民路",
            address="台北市松山區三民路80巷25號",
            lat=25.056119,
            lng=121.564513,
        )
        assert detail.price_wan == 5258
        assert isinstance(detail.price_wan, int)
        assert detail.rooms == 3
        assert detail.floor_current == 2
        assert detail.building_age_years == 1.0
        assert detail.total_area_pin == 46.29
        assert not hasattr(detail, "remark")

    def test_sale_house_search_query_no_rooms(self):
        """驗證 SaleHouseSearchQuery 規格合約已無 rooms 欄位"""
        query = SaleHouseSearchQuery(region_id=1, min_price_wan=1000)
        assert not hasattr(query, "rooms")
        assert "rooms" not in SaleHouseSearchQuery.model_fields



class TestNewHouseModels:
    def test_new_house_summary(self):
        summary = NormalizedNewHouseSummary(
            source_hid=138045,
            project_name="長虹MVP",
            project_status="預售屋",
            region_name="台北市",
            section_name="萬華區",
            address="台北市萬華區康定路",
            min_unit_price_wan=79.0,
            max_unit_price_wan=90.0,
            min_area_pin=28.0,
            max_area_pin=41.0,
            developer="長虹建設",
            cover_image_url="https://example.com/project.jpg",
        )
        assert summary.source_hid == 138045
        assert summary.min_unit_price_wan == 79.0
        assert summary.max_unit_price_wan == 90.0
        assert summary.min_area_pin == 28.0

    def test_new_house_detail(self):
        detail = NormalizedNewHouseDetail(
            hid=138045,
            project_name="長虹MVP",
            build_type="預售屋",
            region="台北市",
            section="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            manage_fee_per_pin=150,
            structural_engine="SRC鋼骨鋼筋混凝土結構",
            direction_rule="朝西北",
            layouts=[
                NewHouseLayoutSpec(room_name="二房", rooms_count=2, min_area_pin=28.0, max_area_pin=31.0),
                NewHouseLayoutSpec(room_name="三房", rooms_count=3, min_area_pin=35.0, max_area_pin=41.0),
            ],
            min_unit_price_wan=79.0,
            max_unit_price_wan=90.0,
            base_area_pin=458.59,
            public_ratio_pct=32.89,
            total_households=331,
        )
        assert detail.hid == 138045
        assert len(detail.layouts) == 2
        assert detail.layouts[0].room_name == "二房"
        assert detail.layouts[0].rooms_count == 2
        assert detail.total_households == 331
        assert detail.structural_engine == "SRC鋼骨鋼筋混凝土結構"
