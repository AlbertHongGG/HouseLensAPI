"""HouseLensAPI - 591 新建案模組轉換器 (591 New House Mapper)

內部專用適配轉換器：將 591 特化封包解析正規化為領域純強型別規範。
所有雜質、未清洗字串在進入核心層前必須徹底清洗完畢。
"""

from typing import Any, Dict, List, Optional

from src.domain.new_house import (
    NewHouseLayoutSpec,
    NewHouseParkingSpec,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.providers.source_591.normalizers import (
    clean_optional_str,
    parse_charging_piles,
    parse_coordinate,
    parse_currency_amount,
    parse_households_count,
    parse_int_count,
    parse_parking_planning,
    parse_parking_price_range,
    parse_parking_ratio,
    parse_percent,
    parse_pin,
    parse_range_float,
    parse_room_count,
)


def map_new_house_summary(item: Dict[str, Any]) -> NormalizedNewHouseSummary:
    """將 591 list-search item 正規化為 NormalizedNewHouseSummary"""
    min_unit_price, max_unit_price = parse_range_float(item.get("price"))
    min_area, max_area = parse_range_float(item.get("area"))

    return NormalizedNewHouseSummary(
        provider_id="591",
        external_project_id=str(item.get("hid")),
        name=str(item.get("build_name") or "").strip(),
        housing_status=str(item.get("build_type_name") or "").strip(),
        region_name=str(item.get("region") or "").strip(),
        section_name=str(item.get("section") or "").strip(),
        address=clean_optional_str(item.get("address")) or "",
        min_unit_price_wan=min_unit_price,
        max_unit_price_wan=max_unit_price,
        min_area_pin=min_area,
        max_area_pin=max_area,
        developer=clean_optional_str(item.get("company")),
        cover_image_url=clean_optional_str(item.get("photo_src")),
    )


def map_new_house_detail(
    data: Dict[str, Any],
    summary: Optional[NormalizedNewHouseSummary] = None,
) -> NormalizedNewHouseDetail:
    """將 591 detail/base-info 回應正規化為 NormalizedNewHouseDetail。

    兩層式跨領域統一架構：
    - 第一層 (身分與地理空間標識)：100% 統一自清單 API (summary)。
    - 第二層 (深層建築規劃與規格)：100% 統一自詳情 API (data.housing)。
    """
    housing = data.get("housing") or {}

    # 第一層：身分與地理空間標識 (統一由 summary 提供)
    ext_id = summary.external_project_id if summary else str(housing.get("hid"))
    p_name = summary.name if summary else str(housing.get("build_name") or "").strip()
    housing_status_val = summary.housing_status if summary else clean_optional_str(housing.get("build_type_name"))
    r_name = summary.region_name if summary else str(housing.get("region") or "").strip()
    s_name = summary.section_name if summary else str(housing.get("section") or "").strip()
    addr = summary.address if summary else (clean_optional_str(housing.get("address")) or "")
    cover_url = summary.cover_image_url if summary else clean_optional_str(housing.get("cover"))

    # 1. 房型與坪數結構化解析
    layout_v2_raw = housing.get("layout_v2") or []
    layouts: List[NewHouseLayoutSpec] = []
    if isinstance(layout_v2_raw, list):
        for it in layout_v2_raw:
            if isinstance(it, dict) and "room" in it:
                r_name_item = str(it.get("room") or "").strip()
                r_count = parse_room_count(r_name_item)
                min_a, max_a = parse_range_float(it.get("area"))
                layouts.append(
                    NewHouseLayoutSpec(
                        room_name=r_name_item,
                        rooms_count=r_count,
                        min_area_pin=min_a,
                        max_area_pin=max_a,
                    )
                )

    # 2. 開價單價區間解析 (萬元/坪)
    price_obj = housing.get("price")
    min_price, max_price = parse_range_float(price_obj)

    # 3. 規劃坪數區間解析 (坪)
    area_obj = housing.get("area")
    min_area_val, max_area_val = parse_range_float(area_obj)

    # 4. 基地坪數
    base_area_raw = housing.get("base_area")
    base_area_pin = None
    if isinstance(base_area_raw, dict):
        base_area_pin = parse_pin(base_area_raw.get("area"))
    else:
        base_area_pin = parse_pin(base_area_raw)

    # 5. 管理費 (元/坪/月)
    manage_cost_raw = housing.get("manage_cost")
    manage_fee_per_pin = None
    if isinstance(manage_cost_raw, dict):
        manage_fee_per_pin = parse_currency_amount(manage_cost_raw.get("price"))
    elif manage_cost_raw:
        manage_fee_per_pin = parse_currency_amount(manage_cost_raw)

    # 6. 公設比 (百分比)
    public_ratio_pct = parse_percent(housing.get("ratio"))

    # 7. 總戶數 (純整數)
    total_households = parse_households_count(housing.get("households"))

    # 8. 建物型態、法定用途、土地使用分區
    building_type = clean_optional_str(housing.get("purpose_name"))
    purpose_val = clean_optional_str(housing.get("purpose_other_name"))
    land_division = clean_optional_str(housing.get("land_division"))

    # 9. 時程規劃: 完工交屋期程與公開銷售日期
    handover_time = None
    deal_time_raw = housing.get("deal_time_v2")
    if isinstance(deal_time_raw, dict):
        if not deal_time_raw.get("pending"):
            handover_time = clean_optional_str(deal_time_raw.get("date"))
    elif deal_time_raw:
        handover_time = clean_optional_str(deal_time_raw)
    if not handover_time:
        dt_fallback = housing.get("deal_time")
        if isinstance(dt_fallback, dict):
            handover_time = clean_optional_str(dt_fallback.get("date"))

    open_sell_date = None
    sell_time_raw = housing.get("sell_time")
    if isinstance(sell_time_raw, dict):
        if not sell_time_raw.get("time_pending"):
            open_sell_date = clean_optional_str(
                sell_time_raw.get("date_origin")
            ) or clean_optional_str(sell_time_raw.get("date"))
    elif sell_time_raw:
        open_sell_date = clean_optional_str(sell_time_raw)

    # 10. 車位規劃與充電設備規格解析
    park_price_raw = housing.get("park_price")
    min_p_price, max_p_price = parse_parking_price_range(park_price_raw)
    p_ratio_desc, p_ratio_val = parse_parking_ratio(housing.get("park_ratio"))
    plane_p_cnt, mech_p_cnt = parse_parking_planning(housing.get("park_planning"))
    p_plan_desc = clean_optional_str(housing.get("park_planning"))
    charging_desc, has_charging = parse_charging_piles(housing.get("park_piles"))

    park_style = clean_optional_str(housing.get("park_style"))
    if park_style in ("暫無", "無", "暫無資料"):
        park_style = None

    parking = NewHouseParkingSpec(
        min_parking_price_wan=min_p_price,
        max_parking_price_wan=max_p_price,
        parking_ratio_desc=p_ratio_desc,
        parking_ratio=p_ratio_val,
        parking_planning_desc=p_plan_desc,
        plane_parking_count=plane_p_cnt,
        mechanical_parking_count=mech_p_cnt,
        charging_piles_desc=charging_desc,
        has_charging_piles=has_charging,
        parking_type=park_style,
    )

    # 11. 社區跨領域外部關聯
    external_community_id = None
    cid_raw = housing.get("community_id")
    if cid_raw is not None and str(cid_raw).strip() not in ("0", ""):
        external_community_id = str(cid_raw).strip()
    community_name = clean_optional_str(housing.get("community_name"))
    community_age = parse_int_count(housing.get("community_age"))

    # 12. 基地經緯度坐標
    map_raw = housing.get("map")
    lat_val = None
    lng_val = None
    if isinstance(map_raw, dict):
        lat_val = parse_coordinate(map_raw.get("lat"))
        lng_val = parse_coordinate(map_raw.get("lng"))
    else:
        lat_val = parse_coordinate(housing.get("lat"))
        lng_val = parse_coordinate(housing.get("lng"))

    # 13. 原始建案網址 (100% 取自 meta.og_url，防禦性容錯 share_info.url)
    meta_obj = data.get("meta") or {}
    new_house_url = clean_optional_str(meta_obj.get("og_url"))
    if not new_house_url:
        share_info = data.get("share_info") or {}
        new_house_url = clean_optional_str(share_info.get("url"))

    return NormalizedNewHouseDetail(
        # --- 第一層：身分與地理空間標識 (100% 清單 API summary 唯一來源) ---
        provider_id=summary.provider_id if summary else "591",
        external_project_id=ext_id,
        name=p_name,
        region_name=r_name,
        section_name=s_name,
        address=addr,
        cover_image_url=cover_url,
        url=new_house_url,
        # --- 第二層：深層建築規格、規劃、時程與坐標 (100% 詳情 API 唯一來源) ---
        housing_status=housing_status_val,
        building_type=building_type,
        purpose=purpose_val,
        land_division=land_division,
        handover_time=handover_time,
        open_sell_date=open_sell_date,
        base_area_pin=base_area_pin,
        public_ratio_pct=public_ratio_pct,
        total_households=total_households,
        manage_fee_per_pin=manage_fee_per_pin,
        min_unit_price_wan=min_price,
        max_unit_price_wan=max_price,
        min_area_pin=min_area_val,
        max_area_pin=max_area_val,
        parking=parking,
        layouts=layouts,
        structure=clean_optional_str(housing.get("structural_engine")),
        orientation=clean_optional_str(housing.get("direction_rule")),
        developer_company=clean_optional_str(housing.get("company")),
        builder_company=clean_optional_str(housing.get("build_company")),
        architect_company=clean_optional_str(housing.get("construction_company")),
        sales_agency_company=clean_optional_str(housing.get("sell_company")),
        reception_address=clean_optional_str(housing.get("reception_address")),
        external_community_id=external_community_id,
        community_name=community_name,
        community_age=community_age,
        lat=lat_val,
        lng=lng_val,
    )

