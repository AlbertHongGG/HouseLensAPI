"""Unit Tests for 591 Mappers against Real Captured Data"""

import json
from pathlib import Path
import pytest

from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_591.mappers.community_mapper import (
    Source591CommunityPhotosDTO,
    map_community_detail,
    map_community_summary,
)
from src.providers.source_591.mappers.new_house_mapper import (
    map_new_house_detail,
    map_new_house_summary,
)
from src.providers.source_591.mappers.sale_house_mapper import (
    Source591CommunityEntryDTO,
    Source591PhotosDTO,
    map_sale_house_detail,
    map_sale_house_summary,
)

CAPTURES_DIR = Path(__file__).parent.parent.parent / "封包紀錄"


def load_captured_json(filename: str) -> dict:
    root = Path(__file__).parent.parent.parent
    target_path = None

    # 1. 優先在 591 封包目錄查找
    for p in root.rglob("*" + filename):
        if "591" in p.parts and p.is_file():
            target_path = p
            break

    # 2. 次選任意子目錄查找
    if target_path is None:
        for p in root.rglob("*" + filename):
            if p.is_file():
                target_path = p
                break

    if target_path is None:
        target_path = CAPTURES_DIR / filename

    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
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
        assert isinstance(summary, NormalizedCommunitySummary)
        assert summary.provider_id == "591"
        assert summary.external_community_id == str(items[0]["id"])
        assert summary.community_name == items[0]["name"]
        assert summary.avg_unit_price_wan is not None
        assert summary.coordinates is not None
        assert summary.purpose == "住宅"
        assert summary.housing_status == "新成屋"
        assert summary.shopping_district == "石牌"
        assert summary.transport == "明德"
        assert summary.cover_image_url is not None

    def test_map_community_detail_from_capture(self):
        summary_data = load_captured_json("社區清單 Respond.json")
        summary_items = summary_data.get("data", {}).get("items", [])
        summary = map_community_summary(summary_items[0])

        detail_data = load_captured_json("社區詳情資訊 Respond.json")
        data_block = detail_data.get("data", {})
        detail = map_community_detail(summary, data_block)

        assert isinstance(detail, NormalizedCommunityDetail)
        # 地理與身分資訊 100% 來自 summary
        assert detail.provider_id == summary.provider_id
        assert detail.external_community_id == summary.external_community_id
        assert detail.community_name == summary.community_name
        assert detail.address == summary.address
        assert detail.region_name == summary.region_name
        assert detail.section_name == summary.section_name
        assert detail.coordinates == summary.coordinates
        assert detail.shopping_district == summary.shopping_district
        assert detail.transport == summary.transport
        assert detail.cover_image_url == summary.cover_image_url
        assert detail.url == "https://market.591.com.tw/5855864"

        # 詳細建築與硬體規格 100% 直取自 detail 的 build_info
        assert detail.orientation == "朝北、朝南"
        assert detail.parking_ratio == 1.07
        assert detail.structure == "SRC造"
        assert len(detail.facilities) > 0
        assert detail.building_type == "住宅大樓"
        assert detail.purpose == "住商用"
        assert detail.housing_status == "新成屋"
        assert detail.avg_unit_price_wan == summary.avg_unit_price_wan
        assert detail.avg_unit_price_wan == 94.0
        assert detail.parking_type == "平面式"
        assert detail.min_parking_price_wan == 360.0
        assert detail.max_parking_price_wan == 420.0
        assert detail.base_area_pin == 1446.0
        assert detail.land_division == "第三種住宅區"
        assert detail.landscape_designer == "境業設計工程有限公司"
        assert detail.public_facility_designer == "境業設計工程有限公司"

        # 相簿圖片清單
        assert len(detail.image_urls) > 0
        assert detail.cover_image_url is not None

    def test_community_photos_dto_extraction_and_sorting(self):
        # 模擬 591 社區相簿封包結構 (data.banners.community_images)
        mock_raw_images = [
            {
                "type": "logo",
                "name": "社區外觀",
                "images": [
                    {
                        "photo": "https://img.591.com.tw/logo_std.jpg",
                        "bigphoto": "https://img.591.com.tw/logo_big.jpg",
                        "maxphoto": "https://img.591.com.tw/logo_max.jpg",
                        "is_video": 0,
                    }
                ],
            },
            {
                "type": "all",
                "name": "全部",
                "images": [
                    {
                        "type": "circum",
                        "name": "周邊環境",
                        "images": [
                            {
                                "photo": "https://img.591.com.tw/circum_std.jpg",
                                "maxphoto": "https://img.591.com.tw/circum_max.jpg",
                                "is_video": 0,
                            },
                            {
                                "photo": "https://img.591.com.tw/video_thumb.jpg",
                                "maxphoto": "https://img.591.com.tw/video_max.jpg",
                                "is_video": 1,  # 影片應被過濾排除
                            },
                        ],
                    },
                    {
                        "type": "logo",
                        "name": "社區外觀",
                        "images": [
                            {
                                "photo": "https://img.591.com.tw/logo_std.jpg",
                                "maxphoto": "https://img.591.com.tw/logo_max.jpg",
                                "is_video": 0,
                            }
                        ],
                    },
                    {
                        "type": "traffic",
                        "name": "交通配套",
                        "images": [
                            {
                                "photo": "https://img.591.com.tw/traffic_std.jpg",
                                "bigphoto": "https://img.591.com.tw/traffic_big.jpg",
                                "maxphoto": "",  # maxphoto 為空時 fallback 到 bigphoto
                                "is_video": 0,
                            }
                        ],
                    },
                ],
            },
        ]

        dto = Source591CommunityPhotosDTO(mock_raw_images)
        # 1. logo 封面置頂於索引 0
        assert dto.cover_url == "https://img.591.com.tw/logo_max.jpg"
        assert dto.image_urls[0] == "https://img.591.com.tw/logo_max.jpg"
        # 2. 影片排除、fallback 正常、去重保序
        assert dto.image_urls == [
            "https://img.591.com.tw/logo_max.jpg",
            "https://img.591.com.tw/circum_max.jpg",
            "https://img.591.com.tw/traffic_big.jpg",
        ]

        # 3. 容錯處理：None 與空結構輸入
        empty_dto = Source591CommunityPhotosDTO(None)
        assert empty_dto.image_urls == []
        assert empty_dto.cover_url is None

        dict_wrapper_dto = Source591CommunityPhotosDTO({"banners": {"community_images": []}})
        assert dict_wrapper_dto.image_urls == []
        assert dict_wrapper_dto.cover_url is None



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
        assert isinstance(real_mapped, NormalizedSaleListing)
        assert real_mapped.external_house_id == "S20604856"
        assert real_mapped.price_wan == 5258
        assert abs(real_mapped.total_area_pin - 46.29) < 0.1
        assert real_mapped.rooms == 3
        assert real_mapped.living_rooms == 2
        assert real_mapped.building_type == "住宅"
        assert real_mapped.has_parking is True
        assert real_mapped.region_name is not None
        assert real_mapped.section_name is not None
        assert not hasattr(real_mapped, "linkman")
        assert not hasattr(real_mapped, "browse_count")

    def test_map_sale_house_detail_from_capture(self):
        data = load_captured_json("房屋物件詳情資訊 Respond.json")
        data_block = data.get("data", {})
        detail = map_sale_house_detail(data_block)

        assert isinstance(detail, NormalizedSalePropertyDetail)
        assert detail.external_house_id == "S20604856"
        assert detail.price_wan == 5258
        assert isinstance(detail.price_wan, int)
        assert detail.rooms == 3
        assert detail.living_rooms == 2
        assert detail.bathrooms == 2
        assert detail.total_area_pin == 46.29
        assert detail.building_type == "住宅"
        assert detail.structure == "電梯大樓"

        # Pure numeric specs
        assert detail.floor_current == 2
        assert detail.floor_total == 24
        assert detail.building_age_years == 1.0
        assert detail.orientation == "坐南朝北"
        assert detail.management_fee_monthly == 4200
        assert detail.public_ratio_pct == 30.0
        assert detail.has_lease is False

        # Area breakdown
        assert detail.main_area_pin == 23.10
        assert detail.auxiliary_area_pin == 2.78
        assert detail.common_area_pin == 11.17
        assert detail.land_area_pin == 5.06
        assert detail.parking_area_pin == 9.24

        # Coordinates
        assert detail.coordinates is not None
        assert detail.coordinates.lat == 25.056119
        assert detail.coordinates.lng == 121.5645131
        assert detail.url == "https://www.591.com.tw/2S?salt=SaI9a&s=a"

        # Summary context injection test
        raw_list = load_captured_json("房屋物件清單 Respond.json")
        summary_candidate = map_sale_house_summary(raw_list.get("data", {}).get("items", [])[1])
        assert summary_candidate is not None
        detail_enriched = map_sale_house_detail(data_block, summary=summary_candidate)
        assert detail_enriched.community_name == summary_candidate.community_name
        assert detail_enriched.external_community_id == summary_candidate.external_community_id
        assert detail_enriched.cover_image_url == summary_candidate.cover_image_url

    def test_parse_floor_magic_99_and_whole_building(self):
        from src.providers.source_591.normalizers import parse_floor

        # 1. 591 清單 API 魔術數字 99 (代表整棟透天/別墅)
        curr, tot, is_whole = parse_floor("99")
        assert curr is None  # 絕不可為 99 樓！
        assert tot is None
        assert is_whole is True

        curr_int, tot_int, is_whole_int = parse_floor(99)
        assert curr_int is None
        assert is_whole_int is True

        # 2. 591 詳情 API 規格 "整棟/5F"
        curr_det, tot_det, is_whole_det = parse_floor("整棟/5F")
        assert curr_det is None
        assert tot_det == 5
        assert is_whole_det is True

        # 3. 一般樓層 "3F/12F"
        curr_norm, tot_norm, is_whole_norm = parse_floor("3F/12F")
        assert curr_norm == 3
        assert tot_norm == 12
        assert is_whole_norm is False

        # 4. 地下室 "B1/7F"
        curr_b1, tot_b1, is_whole_b1 = parse_floor("B1/7F")
        assert curr_b1 == -1
        assert tot_b1 == 7
        assert is_whole_b1 is False

    def test_sale_house_community_addr_never_pollutes_community_name(self):
        # 模擬無社區之公寓/透天項目，含有 community_addr (路街地址) 但 community_info 為空
        mock_raw_item = {
            "houseid": "S12345678",
            "title": "大安區老老公寓三樓",
            "price": "2,500萬",
            "area_price": "80萬",
            "area_str": "31.25坪",
            "floor": "3",
            "all_floor": "4",
            "kindStr": "公寓",
            "region": "台北市",
            "section": "大安區",
            "street_name": "和平東路二段",
            "community_addr": "和平東路二段175巷",  # 路名絕對不可污染為社區名稱！
            "community_info": {},  # 無社區
        }
        listing = map_sale_house_summary(mock_raw_item)
        assert listing is not None
        assert listing.community_name is None
        assert listing.external_community_id is None
        assert listing.floor_current == 3
        assert listing.floor_total == 4
        assert listing.is_whole_building is False

    def test_sale_house_detached_villa_summary_and_detail(self):
        # 模擬透天別墅清單封包 (floor="99", all_floor="5", 有外部社區 ID)
        mock_villa_summary = {
            "houseid": "S99887766",
            "title": "陽明山景觀獨棟別墅",
            "price": "8,800萬",
            "area_str": "120.0坪",
            "floor": "99",
            "all_floor": "5",
            "kindStr": "別墅",
            "region": "台北市",
            "section": "士林區",
            "community_info": {
                "community_id": 5855864,
                "community_name": "陽明山莊",
            },
        }
        summary = map_sale_house_summary(mock_villa_summary)
        assert summary is not None
        assert summary.is_whole_building is True
        assert summary.floor_current is None  # 絕不可為 99 樓！
        assert summary.floor_total == 5
        assert summary.external_community_id == "5855864"
        assert summary.community_name == "陽明山莊"

    def test_sale_community_entry_dto_four_modes(self):
        # 模式 1: 官方代碼 + 名稱 (房仲有勾選)
        mode1_raw = {"info": {"cid": 5855864, "community_name": "鳴森大苑-碧硯閣", "street_keyword": "延壽街"}}
        dto1 = Source591CommunityEntryDTO(mode1_raw)
        assert dto1.cid == 5855864
        assert dto1.normalized_community_id == "5855864"
        assert dto1.normalized_community_name == "鳴森大苑-碧硯閣"
        assert dto1.street_keyword == "延壽街"

        # 模式 2: 無代碼 (cid == 0) 但有真實名稱 (房仲未勾選官方庫，本案核心)
        mode2_raw = {"info": {"cid": 0, "community_name": "吉美富徠", "condition": {"keyword": "瑞安街149巷"}}}
        dto2 = Source591CommunityEntryDTO(mode2_raw)
        assert dto2.cid == 0
        assert dto2.normalized_community_id is None  # 嚴格杜絕魔術數字 '0'
        assert dto2.normalized_community_name == "吉美富徠"
        assert dto2.street_keyword == "瑞安街149巷"

        # 模式 3: 獨立老舊公寓/透天別墅 (cid == 0, community_name == "")
        mode3_raw = {"info": {"cid": 0, "community_name": "", "name": "周邊街道實價登錄"}}
        dto3 = Source591CommunityEntryDTO(mode3_raw)
        assert dto3.cid == 0
        assert dto3.normalized_community_id is None
        assert dto3.normalized_community_name is None

        # 模式 4: 空資料容錯 (data: [] 或 None)
        dto4_empty = Source591CommunityEntryDTO([])
        assert dto4_empty.cid is None
        assert dto4_empty.normalized_community_id is None
        assert dto4_empty.normalized_community_name is None

        dto4_none = Source591CommunityEntryDTO(None)
        assert dto4_none.cid is None
        assert dto4_none.normalized_community_id is None
        assert dto4_none.normalized_community_name is None

    def test_sale_house_detail_atomic_merging_with_community_entry(self):
        mock_detail_raw = {
            "id": "20846137",
            "baseInfo": {
                "title": "瑞安靜巷吉美富徠低公設純住",
                "price": "7,880萬",
                "area": "88.27",
            },
        }

        # 1. 結合模式 2 社區入口資訊 (無 ID，有名稱「吉美富徠」)
        entry_mode2 = {"info": {"cid": 0, "community_name": "吉美富徠"}}
        detail2 = map_sale_house_detail(mock_detail_raw, community_entry=entry_mode2)
        assert detail2.external_house_id == "S20846137"
        assert detail2.external_community_id is None  # ID 為 None
        assert detail2.community_name == "吉美富徠"  # 真實名稱保留！

        # 2. 結合模式 1 社區入口資訊 (有 ID，有名稱)
        entry_mode1 = {"info": {"cid": 5855864, "community_name": "鳴森大苑-碧硯閣"}}
        detail1 = map_sale_house_detail(mock_detail_raw, community_entry=entry_mode1)
        assert detail1.external_community_id == "5855864"
        assert detail1.community_name == "鳴森大苑-碧硯閣"

        # 3. 結合模式 3 (無社區建物)
        entry_mode3 = {"info": {"cid": 0, "community_name": ""}}
        detail3 = map_sale_house_detail(mock_detail_raw, community_entry=entry_mode3)
        assert detail3.external_community_id is None
        assert detail3.community_name is None

    def test_sale_photos_dto_extraction_and_sorting(self):
        mock_raw_photos = {
            "list": [
                {
                    "key": "video",
                    "title": "影片介紹",
                    "list": [
                        {"photo": "https://img.591.com.tw/video_thumb.jpg", "isCover": 0}
                    ],
                },
                {
                    "key": "picture",
                    "title": "房屋相片",
                    "list": [
                        {"photo": "https://img.591.com.tw/room_1.jpg", "isCover": 0},
                        {"photo": "https://img.591.com.tw/living_room_cover.jpg", "isCover": 1},
                        {"photo": "https://img.591.com.tw/kitchen.jpg", "isCover": 0},
                        {"photo": "https://img.591.com.tw/room_1.jpg", "isCover": 0},  # 重複網址
                    ],
                },
                {
                    "key": "picture",
                    "title": "格局圖",
                    "list": [
                        {"photo": "https://img.591.com.tw/layout.jpg", "isCover": 0}
                    ],
                },
            ]
        }
        dto = Source591PhotosDTO(mock_raw_photos)
        # 1. 排除 video
        assert "https://img.591.com.tw/video_thumb.jpg" not in dto.image_urls
        # 2. 封面置頂於索引 0
        assert dto.image_urls[0] == "https://img.591.com.tw/living_room_cover.jpg"
        assert dto.cover_url == "https://img.591.com.tw/living_room_cover.jpg"
        # 3. 去重且保持後續順序
        assert dto.image_urls == [
            "https://img.591.com.tw/living_room_cover.jpg",
            "https://img.591.com.tw/room_1.jpg",
            "https://img.591.com.tw/kitchen.jpg",
            "https://img.591.com.tw/layout.jpg",
        ]

        # 4. 容錯處理：None 與非 dict 輸入
        empty_dto = Source591PhotosDTO(None)
        assert empty_dto.image_urls == []
        assert empty_dto.cover_url is None

    def test_sale_house_detail_atomic_merging_with_photos(self):
        mock_detail_raw = {
            "id": "20846137",
            "baseInfo": {
                "title": "瑞安靜巷吉美富徠低公設純住",
                "price": "7,880萬",
                "area": "88.27",
            },
        }
        mock_photos_raw = {
            "list": [
                {
                    "key": "picture",
                    "list": [
                        {"photo": "https://img.591.com.tw/pic1.jpg", "isCover": 1},
                        {"photo": "https://img.591.com.tw/pic2.jpg", "isCover": 0},
                    ],
                }
            ]
        }

        # 傳入相簿微服務資料
        detail = map_sale_house_detail(mock_detail_raw, photos_data=mock_photos_raw)
        assert detail.image_urls == [
            "https://img.591.com.tw/pic1.jpg",
            "https://img.591.com.tw/pic2.jpg",
        ]
        # 當 detail 本身無封面時，自動回填相簿封面
        assert detail.cover_image_url == "https://img.591.com.tw/pic1.jpg"



class Test591AgeMapper:
    def test_age_str_mapping_single_and_combinations(self):
        from src.providers.source_591.mappers.age_mapper import Source591AgeMapper

        assert Source591AgeMapper.to_age_str(None, 5) == "_5"
        assert Source591AgeMapper.to_age_str(None, 10) == "_5,5_10"
        assert Source591AgeMapper.to_age_str(5, 10) == "5_10"
        assert Source591AgeMapper.to_age_str(10, 30) == "10_20,20_30"
        assert Source591AgeMapper.to_age_str(30, None) == "30_40,40_"
        assert Source591AgeMapper.to_age_str(40, None) == "40_"
        assert Source591AgeMapper.to_age_str(None, None) is None
        assert Source591AgeMapper.to_age_str(0, 100) is None

    def test_age_str_mapping_validation_error(self):
        from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
        with pytest.raises(ValueError):
            Source591AgeMapper.to_age_str(20, 10)

    def test_parse_building_age_strings(self):
        from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
        assert Source591AgeMapper.parse_building_age("1年") == 1.0
        assert Source591AgeMapper.parse_building_age("33.5年") == 33.5
        assert Source591AgeMapper.parse_building_age("全新") == 0.0
        assert Source591AgeMapper.parse_building_age("0年") == 0.0
        assert Source591AgeMapper.parse_building_age("未滿1年") == 0.5
        assert Source591AgeMapper.parse_building_age("3個月") == 0.25
        assert Source591AgeMapper.parse_building_age("6個月") == 0.5
        assert Source591AgeMapper.parse_building_age(None) is None
        assert Source591AgeMapper.parse_building_age("") is None


class Test591NewHouseMappers:
    def test_map_new_house_summary_from_capture(self):
        data = load_captured_json("新建案物件清單 Respond.json")
        items = data.get("data", {}).get("items", [])
        assert len(items) > 0

        summary = map_new_house_summary(items[0])
        assert isinstance(summary, NormalizedNewHouseSummary)
        assert summary.provider_id == "591"
        assert summary.external_project_id == str(items[0]["hid"])
        assert summary.name == items[0]["build_name"]
        assert summary.min_unit_price_wan == 79.0
        assert summary.max_unit_price_wan == 90.0
        assert summary.min_area_pin == 28.0
        assert summary.max_area_pin == 41.0

    def test_map_new_house_detail_from_capture(self):
        data = load_captured_json("新建案物件詳情資訊 Respond.json")
        data_block = data.get("data", {})
        detail = map_new_house_detail(data_block)

        assert isinstance(detail, NormalizedNewHouseDetail)
        assert detail.provider_id == "591"
        assert detail.external_project_id == "138045"
        assert detail.name == "長虹MVP"
        assert detail.region_name == "台北市"
        assert detail.section_name == "萬華區"
        assert detail.structure == "SRC鋼骨鋼筋混凝土結構"
        assert len(detail.layouts) > 0
        assert detail.layouts[0].room_name == "一房"
        assert detail.layouts[0].rooms_count == 1
        assert detail.layouts[0].min_area_pin == 14.0
        assert detail.layouts[0].max_area_pin == 17.0

        # 斷言本次補齊之規格與屬性
        assert detail.building_type == "住宅大樓"
        assert detail.purpose == "住商用"
        assert detail.land_division == "第四種商業區"
        assert detail.handover_time == "預計2028年第一季度"
        assert detail.open_sell_date == "2025-02-01"
        assert detail.architect_company == "簡俊卿建築師事務所"
        assert detail.sales_agency_company == "新聯陽實業機構-新聯信廣告股份有限公司"
        assert detail.external_community_id == "5962516"
        assert detail.community_name == "長虹MVP"
        assert detail.community_age == 0
        assert detail.lat == 25.0444
        assert detail.lng == 121.50265
        assert detail.url == "https://www.591.com.tw/8H?salt=6Zv&s=a"

        # 斷言車位規格值物件 (NewHouseParkingSpec)
        assert detail.parking.min_parking_price_wan == 155.0
        assert detail.parking.max_parking_price_wan == 320.0
        assert detail.parking.parking_ratio_desc == "1:0.46"
        assert detail.parking.parking_ratio == 0.46
        assert detail.parking.parking_planning_desc == "平面式111個、機械式41個"
        assert detail.parking.plane_parking_count == 111
        assert detail.parking.mechanical_parking_count == 41
        assert detail.parking.charging_piles_desc == "有充電設備（含預留）"
        assert detail.parking.has_charging_piles is True
        assert detail.parking.parking_type is None  # 大樓集合住宅 591 封包為「暫無」，防腐層清洗為 None

