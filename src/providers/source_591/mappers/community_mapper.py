"""HouseLensAPI - 591 社區資料模型轉換器 (Community Mapper)"""

from typing import Any, Dict, Optional

from src.domain.common import GeoPoint
from src.domain.community import CommunityDetail, CommunitySummary


def map_community_summary(item: Dict[str, Any]) -> CommunitySummary:
    """將 591 search/list 的原始 item 轉換為標準 CommunitySummary"""
    # 座標解析
    lat = item.get("lat")
    lng = item.get("lng")
    coords: Optional[GeoPoint] = None
    if lat and lng:
        try:
            coords = GeoPoint(lat=float(lat), lng=float(lng))
        except (ValueError, TypeError):
            coords = None

    # 價格解析
    price_obj = item.get("price") or {}
    avg_price: Optional[float] = None
    if isinstance(price_obj, dict):
        raw_price = price_obj.get("price")
        if raw_price is not None:
            try:
                avg_price = float(raw_price)
            except (ValueError, TypeError):
                avg_price = None
        price_unit = price_obj.get("unit")
    else:
        price_unit = None

    # 封面圖解析
    photo_obj = item.get("photo_src") or {}
    cover_url: Optional[str] = None
    if isinstance(photo_obj, dict):
        cover_url = photo_obj.get("src")
    elif isinstance(photo_obj, str):
        cover_url = photo_obj

    region = item.get("region") or ""
    section = item.get("section") or ""
    simple_addr = item.get("simple_address") or ""
    full_addr = f"{region}{section}{simple_addr}"

    return CommunitySummary(
        community_id=str(item.get("id")),
        hid=item.get("hid"),
        community_name=item.get("name") or "",
        build_purpose_simple=item.get("build_purpose_simple"),
        building_type_str=item.get("housing_type_str"),
        region_name=region,
        section_name=section,
        simple_address=simple_addr,
        full_address=full_addr,
        coordinates=coords,
        avg_unit_price=avg_price,
        unit_price_unit=price_unit,
        living_circle_name=item.get("shop_name"),
        nearest_station=item.get("station_name"),
        cover_image_url=cover_url,
    )


def map_community_detail(data: Dict[str, Any]) -> CommunityDetail:
    """將 591 community/info 的原始 data 轉換為標準 CommunityDetail"""
    base_info = data.get("base_info") or {}
    build_info = data.get("build_info") or {}

    # 屋齡解析
    age_obj = build_info.get("age")
    age_str = age_obj.get("content") if isinstance(age_obj, dict) else (str(age_obj) if age_obj else None)

    # 總戶數解析
    house_num_obj = build_info.get("all_house_num")
    total_households = (
        house_num_obj.get("content") if isinstance(house_num_obj, dict) else (str(house_num_obj) if house_num_obj else None)
    )

    # 管理費解析
    manage_obj = build_info.get("manage_cost")
    manage_fee = (
        manage_obj.get("price") if isinstance(manage_obj, dict) else (str(manage_obj) if manage_obj else None)
    )

    # 公設清單
    facility_list = build_info.get("facility") or []
    if isinstance(facility_list, str):
        facility_list = [f.strip() for f in facility_list.split(",") if f.strip()]

    return CommunityDetail(
        community_id=str(base_info.get("community_id")),
        community_name=base_info.get("community_name") or "",
        build_type_str=base_info.get("build_type_str"),
        purpose_str=base_info.get("purpose_str"),
        transport=base_info.get("transport"),
        address=base_info.get("address") or "",
        region_name=base_info.get("region_name") or "",
        section_name=base_info.get("section_name") or "",
        shopping_district=base_info.get("shopping_district"),
        park_rate=build_info.get("park_rate"),
        direction_rule=build_info.get("direction_rule"),
        build_intro=build_info.get("build_intro"),
        landscape_name=build_info.get("landscape_name"),
        postulate_name=build_info.get("postulate_name"),
        park_type_str=build_info.get("park_type_str"),
        age=age_str,
        total_households=total_households,
        floor_plan=build_info.get("floor"),
        structure=build_info.get("structural_engine"),
        base_area_ping=str(build_info.get("base_area_num")) if build_info.get("base_area_num") is not None else None,
        public_ratio=str(build_info.get("ratio")) if build_info.get("ratio") is not None else None,
        parking_count=str(build_info.get("all_park_num")) if build_info.get("all_park_num") is not None else None,
        facilities=facility_list,
        developer_company=build_info.get("company"),
        builder_company=build_info.get("build_company"),
        architect_company=build_info.get("construction_company"),
        management_fee=manage_fee,
    )
