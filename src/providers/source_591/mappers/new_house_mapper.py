"""HouseLensAPI - 591 新建案資料模型轉換器 (New House Mapper)"""

from typing import Any, Dict, List

from src.domain.new_house import NewHouseDetail, NewHouseLayoutItem, NewHouseSummary


def map_new_house_summary(item: Dict[str, Any]) -> NewHouseSummary:
    """將 591 list-search item 轉換為標準 NewHouseSummary"""
    return NewHouseSummary(
        source_hid=int(item.get("hid")),
        project_name=item.get("build_name") or "",
        project_status=item.get("build_type_name") or "",
        region_name=item.get("region") or "",
        section_name=item.get("section") or "",
        address=item.get("address") or "",
        price=str(item.get("price") or ""),
        area=str(item.get("area") or ""),
        room_layout_summary=item.get("room"),
        developer=item.get("company"),
        cover_image_url=item.get("photo_src"),
    )


def map_new_house_detail(data: Dict[str, Any]) -> NewHouseDetail:
    """將 591 detail/base-info 回應轉換為標準 NewHouseDetail。
    
    解析結構化 layout_v2 房型坪數陣列，並擷取完整建案建築與車位規劃規格。
    """
    housing = data.get("housing") or {}

    # layout_v2 結構化解析
    layout_v2_raw = housing.get("layout_v2") or []
    layout_v2_items: List[NewHouseLayoutItem] = []
    if isinstance(layout_v2_raw, list):
        for it in layout_v2_raw:
            if isinstance(it, dict) and "room" in it:
                layout_v2_items.append(
                    NewHouseLayoutItem(
                        room=str(it.get("room")),
                        area=str(it.get("area") or ""),
                    )
                )

    # 管理費字串組裝
    manage_cost_raw = housing.get("manage_cost")
    manage_cost_str: str = ""
    if isinstance(manage_cost_raw, dict):
        p = manage_cost_raw.get("price", "")
        u = manage_cost_raw.get("unit", "")
        manage_cost_str = f"{p} {u}".strip()
    elif manage_cost_raw:
        manage_cost_str = str(manage_cost_raw)

    # 開價字串組裝
    price_obj = housing.get("price")
    unit_price_str = None
    if isinstance(price_obj, dict):
        p = price_obj.get("price", "")
        u = price_obj.get("unit", "")
        unit_price_str = f"{p} {u}".strip() if p else None

    # 基地坪數數值解析
    base_area_ping: float = None
    raw_base_area = housing.get("base_area")
    if raw_base_area is not None:
        try:
            base_area_ping = float(raw_base_area)
        except (ValueError, TypeError):
            base_area_ping = None

    # 車位價格組裝
    park_price_raw = housing.get("park_price")
    park_price_str = None
    if isinstance(park_price_raw, dict):
        p = park_price_raw.get("price", "")
        u = park_price_raw.get("unit", "")
        park_price_str = f"{p}{u}".strip() if p else None
    elif park_price_raw:
        park_price_str = str(park_price_raw)

    return NewHouseDetail(
        hid=int(housing.get("hid")),
        project_name=housing.get("build_name") or "",
        build_type=housing.get("build_type_name") or "",
        region=housing.get("region") or "",
        section=housing.get("section") or "",
        address=housing.get("address") or "",
        manage_cost=manage_cost_str or None,
        structural_engine=housing.get("structural_engine"),
        park_planning=housing.get("park_planning"),
        direction_rule=housing.get("direction_rule"),
        build_intro=housing.get("build_intro"),
        park_ratio=housing.get("park_ratio"),
        layout_v2=layout_v2_items,
        unit_price_str=unit_price_str,
        parking_price_str=park_price_str,
        base_area_ping=base_area_ping,
        public_ratio=str(housing.get("ratio")) if housing.get("ratio") is not None else None,
        total_households=str(housing.get("households")) if housing.get("households") is not None else None,
        developer_company=housing.get("company"),
        builder_company=housing.get("build_company"),
        architect_company=housing.get("construction_company"),
        reception_address=housing.get("reception_address"),
        community_id_ref=housing.get("community_id"),
    )
