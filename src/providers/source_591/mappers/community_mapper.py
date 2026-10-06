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
    clean_optional_str,
    clean_parking_count,
    parse_currency_amount,
    parse_int_count,
    parse_parking_price_range,
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
        cover_url = clean_optional_str(photo_obj.get("src"))
    elif isinstance(photo_obj, str):
        cover_url = clean_optional_str(photo_obj)

    region = str(item.get("region") or "").strip()
    section = str(item.get("section") or "").strip()
    simple_addr = str(item.get("simple_address") or "").strip()
    full_addr = f"{region}{section}{simple_addr}"

    return NormalizedCommunitySummary(
        provider_id="591",
        external_community_id=str(item.get("id")),
        community_name=str(item.get("name") or "").strip(),
        region_name=region,
        section_name=section,
        address=full_addr,
        coordinates=coords,
        avg_unit_price_wan=avg_price,
        building_type=None,
        build_purpose=clean_optional_str(item.get("build_purpose_simple")),
        housing_status=clean_optional_str(item.get("housing_text")),
        shopping_district=clean_optional_str(item.get("shop_name")),
        transport=clean_optional_str(item.get("station_name")),
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
    park_raw = build_info.get("park")
    park_rate_raw = build_info.get("park_rate")
    parking_count = clean_parking_count(
        count_raw=park_num_raw,
        park_raw=park_raw,
        rate_raw=park_rate_raw,
    )

    # 車位價格純數值解析 (min_parking_price_wan, max_parking_price_wan)
    min_park_price, max_park_price = parse_parking_price_range(build_info.get("park_price"))

    # 車位型態空值純化
    park_type_str = clean_optional_str(build_info.get("park_type_str"))

    # 車位配比與公設比解析
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
    base_area_pin = parse_pin(build_info.get("base_area_num"))

    # 土地使用分區
    land_division = clean_optional_str(build_info.get("land_division"))

    # 三維正交解耦映射 (直取 build_info 單一區塊)
    # 1. 建物實體型態 (如: 住宅大樓、華廈、透天、商辦)
    building_type = clean_optional_str(build_info.get("purpose_str"))

    # 2. 法定使用用途 (100% 來自詳情 build_info.purpose_other2)
    build_purpose = clean_optional_str(build_info.get("purpose_other2"))

    # 3. 成屋/建案狀態 (100% 來自詳情 build_info.build_type / build_type_str)
    raw_status_code = build_info.get("build_type")
    raw_status_str = clean_optional_str(build_info.get("build_type_str"))
    if raw_status_str:
        housing_status = raw_status_str
    elif raw_status_code == 1:
        housing_status = "預售屋"
    elif raw_status_code == 2:
        housing_status = "新成屋"
    elif raw_status_code == 5:
        housing_status = "中古屋"
    else:
        housing_status = None

    # 公設清單
    facility_raw = build_info.get("facility") or []
    facility_list = []
    if isinstance(facility_raw, str):
        facility_list = [f.strip() for f in facility_raw.split(",") if f.strip()]
    elif isinstance(facility_raw, list):
        facility_list = [str(f).strip() for f in facility_raw if clean_optional_str(f)]

    return NormalizedCommunityDetail(
        # --- 基礎識別、地理資訊與市場行情：100% 取自清單 (summary，成交均價單一事實來源) ---
        provider_id=summary.provider_id,
        external_community_id=summary.external_community_id,
        community_name=summary.community_name,
        region_name=summary.region_name,
        section_name=summary.section_name,
        address=summary.address,
        coordinates=summary.coordinates,
        avg_unit_price_wan=summary.avg_unit_price_wan,
        cover_image_url=summary.cover_image_url,
        shopping_district=summary.shopping_district,
        transport=summary.transport,
        # --- 建築規格與規劃：100% 取自詳情 build_info 單一區塊 (三維解耦) ---
        building_type=building_type,
        build_purpose=build_purpose,
        housing_status=housing_status,
        total_households=total_households,
        parking_count=parking_count,
        min_parking_price_wan=min_park_price,
        max_parking_price_wan=max_park_price,
        park_type_str=park_type_str,
        parking_ratio_pct=park_ratio,
        public_ratio_pct=public_ratio,
        manage_fee_per_pin=manage_fee,
        base_area_pin=base_area_pin,
        land_division=land_division,
        building_age_years=building_age,
        structure=clean_optional_str(build_info.get("structural_engine")),
        direction_rule=clean_optional_str(build_info.get("direction_rule")),
        floor_plan=clean_optional_str(build_info.get("floor")),
        facilities=facility_list,
        developer_company=clean_optional_str(build_info.get("company")),
        builder_company=clean_optional_str(build_info.get("build_company")),
        architect_company=clean_optional_str(build_info.get("construction_company")),
        landscape_name=clean_optional_str(build_info.get("landscape_name")),
        postulate_name=clean_optional_str(build_info.get("postulate_name")),
    )

