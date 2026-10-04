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


def _extract_cover_image_from_banners(banners: Any) -> Optional[str]:
    """從 591 詳情 banners.community_images 中擷取封面圖片網址"""
    if not isinstance(banners, dict):
        return None
    imgs = banners.get("community_images") or []
    if not isinstance(imgs, list):
        return None

    first_img: Optional[str] = None
    for group in imgs:
        if not isinstance(group, dict):
            continue
        g_imgs = group.get("images") or []
        for item in g_imgs:
            if isinstance(item, dict):
                if "photo" in item or "bigphoto" in item:
                    url = item.get("photo") or item.get("bigphoto") or item.get("maxphoto")
                    if url and not first_img:
                        first_img = url
                elif "images" in item:
                    nested_imgs = item.get("images") or []
                    for n_item in nested_imgs:
                        url = n_item.get("photo") or n_item.get("bigphoto") or n_item.get("maxphoto")
                        if url:
                            if item.get("type") == "logo" or item.get("name") == "封面":
                                return url
                            if not first_img:
                                first_img = url
    return first_img




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
        building_type=item.get("housing_type_str") or item.get("build_type"),
        build_purpose=item.get("build_purpose_simple"),
        living_circle_name=item.get("shop_name"),
        nearest_station=item.get("station_name"),
        cover_image_url=cover_url,
    )


def map_community_detail(data: Dict[str, Any]) -> NormalizedCommunityDetail:
    """將 591 community/info 原始資料清洗為強型別 NormalizedCommunityDetail"""
    base_info = data.get("base_info") or {}
    build_info = data.get("build_info") or {}
    banners = data.get("banners") or {}

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

    # 座標解析：優先從 banners 取得，次由 base_info 取得
    lat = banners.get("lat") or base_info.get("lat")
    lng = banners.get("lng") or base_info.get("lng")
    coords: Optional[GeoPoint] = None
    if lat and lng:
        try:
            coords = GeoPoint(lat=float(lat), lng=float(lng))
        except (ValueError, TypeError):
            coords = None

    # 單價數值化解析 (直取 build_info.price)
    price_obj = build_info.get("price")
    price_raw = price_obj.get("price") if isinstance(price_obj, dict) else (str(price_obj) if price_obj else None)
    avg_price = parse_unit_price(price_raw)

    # 封面圖片解析
    cover_image_url = _extract_cover_image_from_banners(banners)

    # 用途
    build_purpose = base_info.get("purpose_str") or build_info.get("purpose_str")

    # 交通與生活圈商圈
    transport = base_info.get("transport") or build_info.get("subway")
    shopping_district = base_info.get("shopping_district")

    return NormalizedCommunityDetail(
        community_id=str(base_info.get("community_id")),
        community_name=str(base_info.get("community_name") or ""),
        address=str(base_info.get("address") or ""),
        region_name=str(base_info.get("region_name") or ""),
        section_name=str(base_info.get("section_name") or ""),
        coordinates=coords,
        avg_unit_price_wan=avg_price,
        total_households=total_households,
        parking_count=parking_count,
        parking_ratio_pct=park_ratio,
        public_ratio_pct=public_ratio,
        manage_fee_per_pin=manage_fee,
        base_area_pin=base_area,
        building_age_years=building_age,
        building_type=base_info.get("build_type_str") or build_info.get("build_type_str"),
        build_purpose=build_purpose,
        structure=build_info.get("structural_engine"),
        direction_rule=build_info.get("direction_rule"),
        floor_plan_desc=build_info.get("floor"),
        park_type_str=build_info.get("park_type_str"),
        shopping_district=shopping_district,
        transport=transport,
        landscape_name=build_info.get("landscape_name"),
        postulate_name=build_info.get("postulate_name"),
        cover_image_url=cover_image_url,
        facilities=facility_list,
        developer_company=build_info.get("company"),
        builder_company=build_info.get("build_company"),
        architect_company=build_info.get("construction_company"),
    )
