"""Unit Tests for New House Enrichment, Parking Specs & Clean Architecture Invariants

涵蓋建物型態、法定用途、時程規劃、車位規格值物件 (含透天停車風格)、團隊代銷、關聯社區與經緯度坐標。
"""

import pytest
from rich.console import Console

from src.cli.views.new_house_views import new_house_to_dict, render_new_house_detail_view, render_new_house_table
from src.domain.new_house import (
    NewHouseLayoutSpec,
    NewHouseParkingSpec,
    NormalizedNewHouseDetail,
)
from src.providers.source_591.mappers.new_house_mapper import map_new_house_detail
from src.providers.source_591.normalizers import (
    parse_charging_piles,
    parse_coordinate,
    parse_parking_planning,
    parse_parking_price_range,
    parse_parking_ratio,
)
from src.storage.database import DatabaseManager
from src.storage.models.new_house import NewHouseTable
from src.storage.repositories.new_house_repo import NewHouseRepository


class TestNewHouseNormalizers:
    """測試新建案專屬數值與字串正規化解析器"""

    def test_parse_parking_planning_variations(self):
        # 平面 + 機械
        plane, mech = parse_parking_planning("平面式111個、機械式41個")
        assert plane == 111
        assert mech == 41

        # 僅平面
        plane, mech = parse_parking_planning("平面式192個")
        assert plane == 192
        assert mech is None

        # 僅機械
        plane, mech = parse_parking_planning("機械式50個")
        assert plane is None
        assert mech == 50

        # 空格變體
        plane, mech = parse_parking_planning("平面 1 個、機械 33 個")
        assert plane == 1
        assert mech == 33

        # 暫無或無資料
        assert parse_parking_planning("暫無") == (None, None)
        assert parse_parking_planning("") == (None, None)
        assert parse_parking_planning(None) == (None, None)

    def test_parse_parking_ratio_variations(self):
        s, val = parse_parking_ratio("1:0.46")
        assert s == "1:0.46"
        assert val == 0.46

        s, val = parse_parking_ratio("1:1")
        assert s == "1:1"
        assert val == 1.0

        s, val = parse_parking_ratio("1:1.05")
        assert s == "1:1.05"
        assert val == 1.05

        assert parse_parking_ratio("暫無") == (None, None)
        assert parse_parking_ratio(None) == (None, None)

    def test_parse_charging_piles_variations(self):
        desc, has_p = parse_charging_piles("有充電設備（含預留）")
        assert desc == "有充電設備（含預留）"
        assert has_p is True

        desc, has_p = parse_charging_piles("無充電設備")
        assert desc == "無充電設備"
        assert has_p is False

        assert parse_charging_piles("") == (None, None)
        assert parse_charging_piles("暫無") == (None, None)
        assert parse_charging_piles(None) == (None, None)

    def test_parse_parking_price_range_variations(self):
        # 區間價
        min_p, max_p = parse_parking_price_range(
            {"pending": 0, "price": "155~320", "unit": "萬"}
        )
        assert min_p == 155.0
        assert max_p == 320.0

        # 單一價
        min_p, max_p = parse_parking_price_range(
            {"pending": 0, "price": "380", "unit": "萬"}
        )
        assert min_p == 380.0
        assert max_p == 380.0

        # 待定價格
        min_p, max_p = parse_parking_price_range(
            {"pending": 1, "price": "價格待定", "unit": ""}
        )
        assert min_p is None
        assert max_p is None

        # 缺失值
        assert parse_parking_price_range(None) == (None, None)

    def test_parse_coordinate_variations(self):
        assert parse_coordinate("25.04440") == 25.0444
        assert parse_coordinate(121.50265) == 121.50265
        assert parse_coordinate("0") is None
        assert parse_coordinate(0.0) is None
        assert parse_coordinate(None) is None


class TestNewHouseMapperEnrichment:
    """測試 Mapper 對透天建案停車風格、時程與代銷之適配解析"""

    def test_map_detached_house_with_parking_style(self):
        # 模擬透天別墅封包 (park_style="前院停車，1樓停車")
        mock_packet = {
            "housing": {
                "hid": 999901,
                "build_name": "德郡祥賀",
                "build_type_name": "新成屋",
                "purpose_name": "透天",
                "purpose_other_name": "住家用",
                "land_division": "第一種住宅區",
                "region": "台南市",
                "section": "善化區",
                "address": "台南市善化區復興路",
                "deal_time_v2": {"pending": 0, "date": "隨時交屋"},
                "sell_time": {"time_pending": 0, "date_origin": "2024-05-01"},
                "park_style": "前院停車，1樓停車",
                "park_price": {"pending": 1, "price": "價格待定"},
                "park_planning": "平面式2個",
                "park_piles": "無充電設備",
                "company": "德郡建設",
                "construction_company": "大業聯合建築師事務所",
                "sell_company": "自售",
                "community_id": 778899,
                "community_name": "德郡祥賀",
                "community_age": 1,
                "map": {"lat": "23.1345", "lng": "120.2987"},
            }
        }
        detail = map_new_house_detail(mock_packet)
        assert detail.building_type == "透天"
        assert detail.purpose == "住家用"
        assert detail.land_division == "第一種住宅區"
        assert detail.handover_time == "隨時交屋"
        assert detail.open_sell_date == "2024-05-01"
        assert detail.parking.parking_type == "前院停車，1樓停車"
        assert detail.parking.plane_parking_count == 2
        assert detail.parking.has_charging_piles is False
        assert detail.sales_agency_company == "自售"
        assert detail.external_community_id == "778899"
        assert detail.lat == 23.1345
        assert detail.lng == 120.2987


@pytest.mark.asyncio
class TestNewHouseRepositoryAndViews:
    """測試 Repository 的持久化、反查與 CLI 視圖"""

    async def test_repository_upsert_and_community_lookup(self, tmp_path):
        db_file = tmp_path / "test_newhouse.db"
        test_db = DatabaseManager(f"sqlite+aiosqlite:///{db_file}")
        await test_db.init_db()

        p = NewHouseParkingSpec(
            min_parking_price_wan=180.0,
            max_parking_price_wan=250.0,
            parking_ratio_desc="1:1.0",
            parking_ratio=1.0,
            parking_planning_desc="平面式100個",
            plane_parking_count=100,
            mechanical_parking_count=0,
            charging_piles_desc="有充電設備（含預留）",
            has_charging_piles=True,
            parking_type=None,
        )

        detail = NormalizedNewHouseDetail(
            provider_id="591",
            external_project_id="888801",
            name="卓越天廈",
            housing_status="預售屋",
            building_type="住宅大樓",
            purpose="住商用",
            land_division="第二種商業區",
            region_name="新北市",
            section_name="板橋區",
            address="新北市板橋區文化路一段",
            handover_time="預計2027年第四季度",
            open_sell_date="2024-11-01",
            parking=p,
            developer_company="卓越建設",
            builder_company="永固營造",
            architect_company="李祖原建築師事務所",
            sales_agency_company="甲山林廣告",
            external_community_id="556677",
            community_name="卓越天廈",
            community_age=0,
            lat=25.0135,
            lng=121.4658,
            cover_image_url="https://img.example.com/cover.jpg",
            image_urls=["https://img.example.com/nh1.jpg", "https://img.example.com/nh2.jpg"],
        )

        async with test_db.session() as session:
            repo = NewHouseRepository(session)
            # 1. 寫入新紀錄
            record = await repo.upsert_from_detail(detail, "591")
            assert record.name == "卓越天廈"
            assert record.building_type == "住宅大樓"
            assert record.purpose == "住商用"
            assert record.land_division == "第二種商業區"
            assert record.min_parking_price_wan == 180.0
            assert record.max_parking_price_wan == 250.0
            assert record.plane_parking_count == 100
            assert record.has_charging_piles is True
            assert record.sales_agency_company == "甲山林廣告"
            assert record.external_community_id == "556677"
            assert record.lat == 25.0135
            assert record.cover_image_url == "https://img.example.com/cover.jpg"
            assert record.image_urls == ["https://img.example.com/nh1.jpg", "https://img.example.com/nh2.jpg"]

            # 2. 透過社區外部 ID 反查
            results = await repo.get_by_external_community_id("591", "556677")
            assert len(results) == 1
            assert results[0].external_project_id == "888801"

            # 3. 測試視圖與字典輸出
            console = Console(record=True, width=80)
            view = render_new_house_detail_view(record)
            console.print(view)
            output_text = console.export_text()
            assert "卓越天廈" in output_text
            assert "住宅大樓" in output_text
            assert "李祖原建築師事務所" in output_text
            assert "甲山林廣告" in output_text
            assert "相簿照片數量" in output_text

            # 4. 測試字典結構 (JSON 輸出)
            d = new_house_to_dict(record)
            assert d["external_project_id"] == "888801"
            assert d["building_type"] == "住宅大樓"
            assert d["parking"]["min_parking_price_wan"] == 180.0
            assert d["parking"]["plane_parking_count"] == 100
            assert d["external_community_id"] == "556677"
            assert d["image_urls"] == ["https://img.example.com/nh1.jpg", "https://img.example.com/nh2.jpg"]

        await test_db.close()

