"""HouseLensAPI - 591 社區資料模型正規化轉換器 (591 Community Mapper)

將原始 591 社區封包在模組內部完全清洗，直接輸出 NormalizedCommunitySummary 與 NormalizedCommunityDetail。
"""

from typing import Any, Dict, Optional

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.normalizers import (
    parse_currency_amount,
    parse_int_count,
    parse_percent,
    parse_pin,
    parse_unit_price,
)


def map_community_summary(item: Dict[str, Any]) -> NormalizedCommunitySummary:
    """將 591 search/list 原始項目轉換為標準 NormalizedCommunitySummary (基礎識別與地理唯一來源)"""
    # 座標解析 (唯一正規來源：清單 API)
    lat = item.get("lat")
    lng = item.get("lng")
    coords: Optional[GeoPoint] = None
    if lat and lng:
        try:
            coords = GeoPoint(lat=float(lat), lng=float(lng))
        except (ValueError, TypeError):
            coords = None

    # 單價數值化解析
    price_obj = item.get("price") or {}
    avg_price: Optional[float] = None
    if isinstance(price_obj, dict):
        avg_price = parse_unit_price(price_obj.get("price"))

    # 封面圖解析 (唯一正規來源：清單 API)
    photo_obj = item.get("photo_src") or {}
    cover_url: Optional[str] = None
    if isinstance(photo_obj, dict):
        cover_url = photo_obj.get("src")
    elif isinstance(photo_obj, str):
        cover_url = photo_obj

    region = str(item.get("region") or "")
    section = str(item.get("section") or "")
    simple_addr = str(item.get("simple_address") or "")
    full_addr = f"{region}{section}{simple_addr}"

    return NormalizedCommunitySummary(
        community_id=str(item.get("id")),
        community_name=str(item.get("name") or ""),
        region_name=region,
        section_name=section,
        full_address=full_addr,
        coordinates=coords,
        avg_unit_price_wan=avg_price,
        building_type=None,
        build_purpose=item.get("build_purpose_simple"),
        housing_status=item.get("housing_text"),
        living_circle_name=item.get("shop_name"),
        nearest_station=item.get("station_name"),
        cover_image_url=cover_url,
    )


def map_community_detail(
    summary: NormalizedCommunitySummary,
    data: Dict[str, Any],
) -> NormalizedCommunityDetail:
    """將 591 社區封包組裝為強型別 NormalizedCommunityDetail。

    職責邊界：
    - 基礎身分與地理資訊：100% 來自清單 API (summary)。
    - 建築規劃與深層規格：100% 來自詳情 API build_info 單一區塊，絕不跨區塊抓取。
    """
    build_info = data.get("build_info") or {}

    # 屋齡解析為浮點數
    age_obj = build_info.get("age")
    age_raw = age_obj.get("content") if isinstance(age_obj, dict) else (str(age_obj) if age_obj else None)
    building_age = Source591AgeMapper.parse_building_age(age_raw)

    # 總戶數與車位數純整數解析
    house_num_obj = build_info.get("all_house_num")
    house_raw = house_num_obj.get("content") if isinstance(house_num_obj, dict) else (str(house_num_obj) if house_num_obj else None)
    total_households = parse_int_count(house_raw)

    park_num_raw = build_info.get("all_park_num")
    parking_count = parse_int_count(park_num_raw)

    # 車位價格描述 (如: {"price": "290~330", "unit": "萬"} -> "290~330萬")
    park_price_obj = build_info.get("park_price")
    park_price: Optional[str] = None
    if isinstance(park_price_obj, dict):
        p_val = park_price_obj.get("price")
        p_unit = park_price_obj.get("unit") or "萬"
        if p_val:
            park_price = f"{p_val}{p_unit}"
    elif park_price_obj:
        park_price = str(park_price_obj).strip() or None

    # 車位型態
    park_type_str = build_info.get("park_type_str")

    # 車位配比與公設比解析
    park_rate_raw = build_info.get("park_rate")
    park_ratio = None
    if park_rate_raw and ":" in str(park_rate_raw):
        try:
            parts = str(park_rate_raw).split(":")
            park_ratio = float(parts[1].strip())
        except (ValueError, IndexError):
            park_ratio = None
    elif park_rate_raw:
        park_ratio = parse_unit_price(park_rate_raw)

    public_ratio = parse_percent(build_info.get("ratio"))

    # 管理費單價純整數 (元/坪/月)
    manage_obj = build_info.get("manage_cost")
    manage_raw = manage_obj.get("price") if isinstance(manage_obj, dict) else (str(manage_obj) if manage_obj else None)
    manage_fee = parse_currency_amount(manage_raw)

    # 基地面積純浮點數 (坪)
    base_area_num = parse_pin(build_info.get("base_area_num"))

    # 土地使用分區
    land_division = build_info.get("land_division")

    # 單價數值化解析 (直取 build_info.price)
    price_obj = build_info.get("price")
    price_raw = price_obj.get("price") if isinstance(price_obj, dict) else (str(price_obj) if price_obj else None)
    avg_price = parse_unit_price(price_raw)

    # 三維正交解耦映射 (直取 build_info 單一區塊)
    # 1. 建物實體型態 (如: 住宅大樓、華廈、透天、商辦)
    building_type = build_info.get("purpose_str")

    # 2. 法定使用用途 (如: 住家用、住商用、商業用)
    build_purpose = build_info.get("purpose_other2") or summary.build_purpose

    # 3. 成屋/建案狀態 (如: 預售屋、新成屋、中古屋)
    raw_status_code = build_info.get("build_type")
    raw_status_str = (build_info.get("build_type_str") or "").strip()
    if raw_status_str:
        housing_status = raw_status_str
    elif raw_status_code == 1:
        housing_status = "預售屋"
    elif raw_status_code == 2:
        housing_status = "新成屋"
    elif raw_status_code == 5:
        housing_status = "中古屋"
    else:
        housing_status = summary.housing_status

    # 公設清單
    facility_list = build_info.get("facility") or []
    if isinstance(facility_list, str):
        facility_list = [f.strip() for f in facility_list.split(",") if f.strip()]

    return NormalizedCommunityDetail(
        # --- 基礎識別與地理資訊：100% 取自清單 (summary) ---
        community_id=summary.community_id,
        community_name=summary.community_name,
        region_name=summary.region_name,
        section_name=summary.section_name,
        address=summary.full_address,
        coordinates=summary.coordinates,
        cover_image_url=summary.cover_image_url,
        shopping_district=summary.shopping_district,
        transport=summary.transport,
        # --- 建築規格與規劃：100% 取自詳情 build_info 單一區塊 (三維解耦) ---
        building_type=building_type,
        build_purpose=build_purpose,
        housing_status=housing_status,
        avg_unit_price_wan=avg_price,
        total_households=total_households,
        parking_count=parking_count,
        park_price=park_price,
        park_type_str=park_type_str,
        parking_ratio_pct=park_ratio,
        public_ratio_pct=public_ratio,
        manage_fee_per_pin=manage_fee,
        base_area_num=base_area_num,
        land_division=land_division,
        building_age_years=building_age,
        structure=build_info.get("structural_engine"),
        direction_rule=build_info.get("direction_rule"),
        floor_plan_desc=build_info.get("floor"),
        facilities=facility_list,
        developer_company=build_info.get("company"),
        builder_company=build_info.get("build_company"),
        architect_company=build_info.get("construction_company"),
        landscape_name=build_info.get("landscape_name"),
        postulate_name=build_info.get("postulate_name"),
    )
