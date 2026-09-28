"""HouseLensAPI - 591 中古屋資料模型轉換器 (Sale House Mapper)

全量過濾廣告物件，將原始 591 封包深度清洗為無冗餘、跨平台統一之 SaleHouseSummary 與 SaleHouseDetail。
"""

from typing import Any, Dict, Optional

from src.domain.sale_house import SaleHouseDetail, SaleHouseSummary


def map_sale_house_summary(item: Dict[str, Any]) -> Optional[SaleHouseSummary]:
    """將 591 sale/list 項目轉換為標準 SaleHouseSummary。
    
    若為廣告項目 (is_ads == "1") 則回傳 None。
    """
    # 嚴格過濾廣告推廣建案/外部廣告
    if str(item.get("is_ads")) == "1":
        return None

    # 權狀坪數解析
    area_obj = item.get("areaUnit") or {}
    total_area: Optional[float] = None
    if isinstance(area_obj, dict):
        raw_area = area_obj.get("area")
        if raw_area:
            try:
                total_area = float(raw_area)
            except (ValueError, TypeError):
                total_area = None

    # 社區名稱解析
    comm_info = item.get("community_info")
    comm_name: Optional[str] = None
    if isinstance(comm_info, dict):
        comm_name = comm_info.get("community_name")
    if not comm_name:
        comm_name = item.get("community_addr")

    return SaleHouseSummary(
        house_id=str(item.get("houseid")),
        title=item.get("title") or "",
        price=item.get("price") or "",
        unit_price=item.get("area_price"),
        total_area=total_area,
        layout=item.get("layout_str"),
        building_type=item.get("kindStr"),
        region=item.get("region") or "",
        section=item.get("section") or "",
        street=item.get("street_name"),
        address=item.get("address"),
        community_id=item.get("community_id"),
        community_name=comm_name,
        floor=item.get("floor"),
        total_floor=item.get("all_floor"),
        has_parking=str(item.get("cartplace")) == "1",
        cover_image_url=item.get("photo_src"),
    )


def map_sale_house_detail(data: Dict[str, Any]) -> SaleHouseDetail:
    """將 591 sale/detail 回應轉換為跨平台標準 SaleHouseDetail。
    
    深入解析 10 大建築規格與 6 大產權坪數拆解，排除平台特化欄位與冗餘。
    """
    base_info = data.get("baseInfo") or {}
    address_info = base_info.get("address") or {}

    # 1. 解析 baseInfo.info 規格字典
    info_list = base_info.get("info") or []
    info_dict = {
        item.get("name"): item.get("value")
        for item in info_list
        if isinstance(item, dict) and "name" in item
    }

    # 2. 解析 baseInfo.areaIntro 產權坪數明細字典
    area_list = base_info.get("areaIntro") or []
    area_dict = {
        item.get("name"): item.get("value")
        for item in area_list
        if isinstance(item, dict) and "name" in item
    }

    # 土地持份相容性解析 (多筆實測兼顧 '土地持分坪數' 與 '土地坪數')
    land_area = area_dict.get("土地持分坪數") or area_dict.get("土地坪數")

    # 3. 座標浮點數解析
    lat: Optional[float] = None
    lng: Optional[float] = None
    raw_lat = address_info.get("lat")
    raw_lng = address_info.get("lng")
    if raw_lat and raw_lng:
        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
        except (ValueError, TypeError):
            lat, lng = None, None

    # 4. 總登記坪數浮點數解析
    total_area: Optional[float] = None
    raw_total_area = base_info.get("area")
    if raw_total_area is not None:
        try:
            total_area = float(raw_total_area)
        except (ValueError, TypeError):
            total_area = None

    # 5. 總價純整數解析 (原生 int)
    price_val: int = 0
    raw_price = base_info.get("price")
    if raw_price is not None:
        try:
            price_val = int(raw_price)
        except (ValueError, TypeError):
            price_val = 0

    # 6. 地址組裝 (若缺少完整地址，由結構化路徑自動拼裝)
    region_str = address_info.get("region") or ""
    section_str = address_info.get("section") or ""
    street_str = address_info.get("street") or ""
    addr_str = address_info.get("addr") or ""
    num_str = f"{address_info.get('addr_number')}號" if address_info.get("addr_number") else ""
    full_address = f"{region_str}{section_str}{street_str}{addr_str}{num_str}"

    return SaleHouseDetail(
        house_id=str(data.get("id")),
        title=base_info.get("title") or "",
        price=price_val,
        unit_price=base_info.get("unitPrice"),
        layout=base_info.get("layout"),
        total_area=total_area,
        building_type=data.get("kindStr"),
        building_structure=info_dict.get("型態"),
        # 建築規格
        floor=info_dict.get("樓層"),
        age=info_dict.get("屋齡"),
        orientation=info_dict.get("朝向"),
        management_fee=info_dict.get("管理費"),
        public_ratio=info_dict.get("公設比"),
        has_lease=info_dict.get("帶租約"),
        balcony=info_dict.get("陽台"),
        purpose=info_dict.get("用途"),
        current_state=info_dict.get("現況"),
        parking_desc=base_info.get("parking"),
        # 產權面積明細
        main_building_area=area_dict.get("主建物"),
        auxiliary_area=area_dict.get("附屬建物"),
        common_area=area_dict.get("共有部分"),
        land_area=land_area,
        parking_area=area_dict.get("車位面積"),
        # 結構化地理座標
        region=region_str or None,
        section=section_str or None,
        street=street_str or None,
        address=full_address or None,
        lat=lat,
        lng=lng,
    )
