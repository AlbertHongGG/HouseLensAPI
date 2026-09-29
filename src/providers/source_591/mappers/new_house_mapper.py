"""HouseLensAPI - 591 新建案模組轉換器 (591 New House Mapper)

內部專用適配轉換器：將 591 特化封包解析正規化為領域純強型別規範。
所有雜質、未清洗字串在進入核心層前必須徹底清洗完畢。
"""

from typing import Any, Dict, List

from src.domain.new_house import (
    NewHouseLayoutSpec,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.providers.source_591.normalizers import (
    parse_currency_amount,
    parse_households_count,
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
        source_hid=int(item.get("hid")),
        project_name=item.get("build_name") or "",
        project_status=item.get("build_type_name") or "",
        region_name=item.get("region") or "",
        section_name=item.get("section") or "",
        address=item.get("address") or "",
        min_unit_price_wan=min_unit_price,
        max_unit_price_wan=max_unit_price,
        min_area_pin=min_area,
        max_area_pin=max_area,
        room_summary=item.get("room"),
        developer=item.get("company"),
        cover_image_url=item.get("photo_src"),
    )


def map_new_house_detail(data: Dict[str, Any]) -> NormalizedNewHouseDetail:
    """將 591 detail/base-info 回應正規化為 NormalizedNewHouseDetail。"""
    housing = data.get("housing") or {}

    # 1. 房型與坪數結構化解析
    layout_v2_raw = housing.get("layout_v2") or []
    layouts: List[NewHouseLayoutSpec] = []
    if isinstance(layout_v2_raw, list):
        for it in layout_v2_raw:
            if isinstance(it, dict) and "room" in it:
                r_name = str(it.get("room") or "").strip()
                r_count = parse_room_count(r_name)
                min_a, max_a = parse_range_float(it.get("area"))
                layouts.append(
                    NewHouseLayoutSpec(
                        room_name=r_name,
                        rooms_count=r_count,
                        min_area_pin=min_a,
                        max_area_pin=max_a,
                    )
                )

    # 2. 開價單價區間解析 (萬元/坪)
    price_obj = housing.get("price")
    min_price, max_price = parse_range_float(price_obj)

    # 3. 基地坪數
    base_area_raw = housing.get("base_area")
    base_area_pin = None
    if isinstance(base_area_raw, dict):
        base_area_pin = parse_pin(base_area_raw.get("area"))
    else:
        base_area_pin = parse_pin(base_area_raw)

    # 4. 管理費 (元/坪/月)
    manage_cost_raw = housing.get("manage_cost")
    manage_fee_per_pin = None
    if isinstance(manage_cost_raw, dict):
        manage_fee_per_pin = parse_currency_amount(manage_cost_raw.get("price"))
    elif manage_cost_raw:
        manage_fee_per_pin = parse_currency_amount(manage_cost_raw)

    # 5. 公設比 (百分比)
    public_ratio_pct = parse_percent(housing.get("ratio"))

    # 6. 總戶數 (純整數)
    total_households = parse_households_count(housing.get("households"))

    return NormalizedNewHouseDetail(
        hid=int(housing.get("hid")),
        project_name=housing.get("build_name") or "",
        build_type=housing.get("build_type_name") or "",
        region=housing.get("region") or "",
        section=housing.get("section") or "",
        address=housing.get("address") or "",
        base_area_pin=base_area_pin,
        public_ratio_pct=public_ratio_pct,
        total_households=total_households,
        manage_fee_per_pin=manage_fee_per_pin,
        min_unit_price_wan=min_price,
        max_unit_price_wan=max_price,
        layouts=layouts,
        structural_engine=housing.get("structural_engine"),
        direction_rule=housing.get("direction_rule"),
        build_intro=housing.get("build_intro"),
        developer_company=housing.get("company"),
        builder_company=housing.get("build_company"),
        architect_company=housing.get("construction_company"),
        reception_address=housing.get("reception_address"),
    )
