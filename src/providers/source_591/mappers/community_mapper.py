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
    """將 591 search/list 原始項目轉換為標準 NormalizedCommunitySummary"""
    # 座標解析
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

    # 封面圖解析
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
        building_type=item.get("housing_type_str") or item.get("build_purpose_simple"),
        living_circle_name=item.get("shop_name"),
        nearest_station=item.get("station_name"),
        cover_image_url=cover_url,
    )


def map_community_detail(data: Dict[str, Any]) -> NormalizedCommunityDetail:
    """將 591 community/info 原始資料清洗為強型別 NormalizedCommunityDetail"""
    base_info = data.get("base_info") or {}
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
    base_area = parse_pin(build_info.get("base_area_num"))

    # 公設清單
    facility_list = build_info.get("facility") or []
    if isinstance(facility_list, str):
        facility_list = [f.strip() for f in facility_list.split(",") if f.strip()]

    # 座標解析
    lat = base_info.get("lat")
    lng = base_info.get("lng")
    coords: Optional[GeoPoint] = None
    if lat and lng:
        try:
            coords = GeoPoint(lat=float(lat), lng=float(lng))
        except (ValueError, TypeError):
            coords = None

    return NormalizedCommunityDetail(
        community_id=str(base_info.get("community_id")),
        community_name=str(base_info.get("community_name") or ""),
        address=str(base_info.get("address") or ""),
        region_name=str(base_info.get("region_name") or ""),
        section_name=str(base_info.get("section_name") or ""),
        coordinates=coords,
        total_households=total_households,
        parking_count=parking_count,
        parking_ratio_pct=park_ratio,
        public_ratio_pct=public_ratio,
        manage_fee_per_pin=manage_fee,
        base_area_pin=base_area,
        building_age_years=building_age,
        building_type=base_info.get("build_type_str"),
        purpose=base_info.get("purpose_str"),
        structure=build_info.get("structural_engine"),
        direction_rule=build_info.get("direction_rule"),
        floor_plan_desc=build_info.get("floor"),
        facilities=facility_list,
        developer_company=build_info.get("company"),
        builder_company=build_info.get("build_company"),
        architect_company=build_info.get("construction_company"),
        build_intro=build_info.get("build_intro"),
    )
