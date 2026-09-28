"""Unit Tests for HouseLensAPI Domain Models"""

import pytest
from pydantic import ValidationError

from src.domain.enums import Region, BuildingType, NewHouseStatus, AgeRange
from src.domain.common import GeoPoint, StructuredAddress, PageQuery, PageResult
from src.domain.community import CommunitySummary, CommunityDetail, CommunitySearchQuery
from src.domain.sale_house import SaleHouseSummary, SaleHouseDetail, SaleHouseSearchQuery
from src.domain.new_house import NewHouseLayoutItem, NewHouseSummary, NewHouseDetail, NewHouseSearchQuery


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
        summary = CommunitySummary(
            community_id="5934204",
            hid=134475,
            community_name="鳴森大苑-鳴森苑",
            build_purpose_simple="住宅",
            building_type_str="新成屋",
            region_name="台北市",
            section_name="松山區",
            simple_address="延壽街72巷...",
            full_address="台北市松山區延壽街72巷...",
            coordinates=GeoPoint(lat=25.056, lng=121.564),
            avg_unit_price=141.0,
            unit_price_unit="萬/坪",
            living_circle_name="民生社區",
            nearest_station="南京三民站",
            cover_image_url="https://example.com/cover.jpg",
        )
        assert summary.community_id == "5934204"
        assert summary.avg_unit_price == 141.0
        assert summary.coordinates.lat == 25.056

    def test_community_detail_instantiation(self):
        detail = CommunityDetail(
            community_id="5934204",
            community_name="鳴森大苑-鳴森苑",
            address="台北市松山區延壽街72巷",
            region_name="台北市",
            section_name="松山區",
            park_rate="1:1.07",
            direction_rule="朝北、朝南",
            build_intro="SRC雙制震，戶戶三面採光",
            facilities=["接待大廳", "空中花園"],
            management_fee="150元/坪/月",
        )
        assert detail.community_id == "5934204"
        assert len(detail.facilities) == 2
        assert detail.direction_rule == "朝北、朝南"


class TestSaleHouseModels:
    def test_sale_house_summary_clean_contract(self):
        summary = SaleHouseSummary(
            house_id="S20604856",
            title="全新碧硯閣三房車位",
            price="5,258萬元",
            unit_price="132.2萬/坪",
            total_area=46.3,
            layout="3房2廳",
            building_type="住宅",
            region="台北市",
            section="松山區",
            street="三民路",
            address="鳴森大苑-碧硯閣 松山區-三民路",
            community_id="5855864",
            community_name="鳴森大苑-碧硯閣",
            floor="2",
            total_floor="24",
            has_parking=True,
            cover_image_url="https://example.com/house.jpg",
        )
        assert summary.house_id == "S20604856"
        assert summary.total_area == 46.3
        assert summary.has_parking is True
        assert not hasattr(summary, "linkman")
        assert not hasattr(summary, "browse_count")

    def test_sale_house_detail_cross_platform_contract(self):
        detail = SaleHouseDetail(
            house_id="20604856",
            title="全新碧硯閣三房車位",
            price=5258,
            unit_price="132.2萬/坪",
            layout="3房2廳2衛",
            total_area=46.29,
            building_type="住宅",
            building_structure="電梯大樓",
            floor="2F/24F",
            age="1年",
            orientation="坐南朝北",
            management_fee="4200元/月",
            public_ratio="30%",
            has_lease="否",
            balcony="1個",
            purpose="住家用",
            current_state="住宅",
            parking_desc="9.24坪，平面式，已含售金內",
            main_building_area="23.10坪",
            auxiliary_area="2.78坪",
            common_area="11.17坪",
            land_area="5.06坪",
            parking_area="9.24坪",
            region="台北市",
            section="松山區",
            street="三民路",
            address="台北市松山區三民路80巷25號",
            lat=25.056119,
            lng=121.564513,
        )
        assert detail.price == 5258
        assert isinstance(detail.price, int)
        assert detail.layout == "3房2廳2衛"
        assert detail.total_area == 46.29
        # Check no redundant room, shape, or main_area
        assert not hasattr(detail, "room")
        assert not hasattr(detail, "shape")
        assert not hasattr(detail, "main_area")
        assert not hasattr(detail, "remark")


class TestNewHouseModels:
    def test_new_house_summary(self):
        summary = NewHouseSummary(
            source_hid=138045,
            project_name="長虹MVP",
            project_status="預售屋",
            region_name="台北市",
            section_name="萬華區",
            address="台北市萬華區康定路",
            price="79~90",
            area="28~41坪",
            room_layout_summary="2~4房",
            developer="長虹建設",
            cover_image_url="https://example.com/project.jpg",
        )
        assert summary.source_hid == 138045
        assert summary.price == "79~90"
        assert summary.area == "28~41坪"
        assert not hasattr(summary, "price_unit")

    def test_new_house_detail(self):
        detail = NewHouseDetail(
            hid=138045,
            project_name="長虹MVP",
            build_type="預售屋",
            region="台北市",
            section="萬華區",
            address="台北市萬華區康定路、峨眉街口",
            manage_cost="150 元/坪/月",
            structural_engine="SRC鋼骨鋼筋混凝土結構",
            park_planning="平面式111個、機械式41個",
            direction_rule="朝西北",
            build_intro="廚具:林內，衛浴:INAX",
            park_ratio="1:0.46",
            layout_v2=[
                NewHouseLayoutItem(room="二房", area="28~31"),
                NewHouseLayoutItem(room="三房", area="35~41"),
            ],
            unit_price_str="79~90 萬/坪",
        )
        assert detail.hid == 138045
        assert len(detail.layout_v2) == 2
        assert detail.layout_v2[0].room == "二房"
        assert detail.structural_engine == "SRC鋼骨鋼筋混凝土結構"
