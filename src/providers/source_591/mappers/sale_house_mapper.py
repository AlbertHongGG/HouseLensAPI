"""HouseLensAPI - 591 中古屋模組資料正規化映射器 (591 Sale House Mapper)

將原始 591 封包在模組內部徹底清洗與正規化，直接輸出符合核心標準的
NormalizedSaleListing 與 NormalizedSalePropertyDetail。
"""

from typing import Any, Dict, Optional

from src.domain.common import GeoPoint
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.mappers.sale_house_validator import Source591SaleHouseValidator
from src.providers.source_591.normalizers import (
    clean_optional_str,
    parse_boolean,
    parse_currency_amount,
    parse_floor,
    parse_int_count,
    parse_layout,
    parse_percent,
    parse_pin,
    parse_price_wan,
    parse_unit_price,
)


def map_sale_house_summary(item: Dict[str, Any]) -> Optional[NormalizedSaleListing]:
    """將 591 sale/list 原始項目轉換為標準 NormalizedSaleListing。

    透過 Source591SaleHouseValidator 進行嚴格合法性過濾：
    凡虛擬競價置頂卡片 (S25)、已定交成交下架卡片、顯式廣告標籤 (is_ads == '1')，一律回傳 None。
    """
    if not Source591SaleHouseValidator.is_valid_sale_house(item):
        return None

    # 1. 權狀總坪數數值化解析
    total_area_pin: float = 0.0
    area_obj = item.get("areaUnit") or {}
    if isinstance(area_obj, dict) and area_obj.get("area"):
        parsed = parse_pin(area_obj.get("area"))
        if parsed is not None:
            total_area_pin = parsed
    if total_area_pin == 0.0:
        parsed = parse_pin(item.get("area_str"))
        if parsed is not None:
            total_area_pin = parsed

    # 2. 價格與單價數值化解析
    price_wan = parse_price_wan(item.get("price"))
    unit_price_wan = parse_unit_price(item.get("area_price"))

    # 3. 樓層與格局數值化解析
    floor_curr, floor_tot = parse_floor(item.get("floor"))
    if floor_tot is None and item.get("all_floor"):
        _, parsed_tot = parse_floor(item.get("all_floor"))
        floor_tot = parsed_tot or parse_int_count(item.get("all_floor"))

    rooms, living, baths = parse_layout(item.get("layout_str"))

    # 4. 社區名稱解析
    comm_info = item.get("community_info")
    comm_name: Optional[str] = None
    if isinstance(comm_info, dict):
        comm_name = comm_info.get("community_name")
    if not comm_name:
        comm_name = item.get("community_addr")

    raw_hid = str(item.get("houseid") or "").strip().upper()
    canonical_hid = raw_hid if raw_hid.startswith("S") else f"S{raw_hid}"

    return NormalizedSaleListing(
        provider_id="591",
        external_house_id=canonical_hid,
        title=str(item.get("title") or "").strip(),
        price_wan=price_wan,
        unit_price_wan=unit_price_wan,
        total_area_pin=total_area_pin,
        floor_current=floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=living,
        bathrooms=baths,
        building_age_years=None,  # 591 清單端點無屋齡欄位，詳情端點補齊
        building_type=clean_optional_str(item.get("kindStr")),
        region_name=str(item.get("region") or "").strip(),
        section_name=str(item.get("section") or "").strip(),
        street=clean_optional_str(item.get("street_name")),
        address=clean_optional_str(item.get("address")),
        community_id=clean_optional_str(item.get("community_id")),
        community_name=clean_optional_str(comm_name),
        has_parking=str(item.get("cartplace")) == "1",
        cover_image_url=clean_optional_str(item.get("photo_src")),
    )


def map_sale_house_detail(
    data: Dict[str, Any],
    summary: Optional[NormalizedSaleListing] = None,
) -> NormalizedSalePropertyDetail:
    """將 591 sale/detail 回應在模組內部清洗為標準 NormalizedSalePropertyDetail。

    所有欄位皆以強型別數值封裝，徹底杜絕文字殘留。
    若提供 summary 上下文，則社區代號、社區名稱、封面縮圖等清單專屬資訊將完整繼承注入。
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

    # 2. 解析 baseInfo.areaIntro 產權坪數字典 (直接轉 float)
    area_list = base_info.get("areaIntro") or []
    area_dict = {
        item.get("name"): item.get("value")
        for item in area_list
        if isinstance(item, dict) and "name" in item
    }

    main_area = parse_pin(area_dict.get("主建物"))
    aux_area = parse_pin(area_dict.get("附屬建物"))
    common_area = parse_pin(area_dict.get("共有部分"))
    land_area = parse_pin(area_dict.get("土地持分坪數") or area_dict.get("土地坪數"))
    parking_area = parse_pin(area_dict.get("車位面積"))

    # 3. 樓層與格局數值化
    floor_curr, floor_tot = parse_floor(info_dict.get("樓層"))
    rooms, living, baths = parse_layout(base_info.get("layout"))

    # 4. 座標浮點數解析
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

    # 5. 總登記坪數浮點數 (詳情為權威來源，若無則以 summary 補底)
    total_area = parse_pin(base_info.get("area"))
    if total_area is None and summary:
        total_area = summary.total_area_pin
    if total_area is None:
        total_area = 0.0

    # 6. 金額與單價 (詳情為權威來源，若無則以 summary 補底)
    price_wan = parse_price_wan(base_info.get("price"))
    if price_wan == 0 and summary:
        price_wan = summary.price_wan

    unit_price = parse_unit_price(base_info.get("unitPrice"))
    if unit_price is None and summary:
        unit_price = summary.unit_price_wan

    # 7. 屋齡、公設比、管理費數值化
    building_age = Source591AgeMapper.parse_building_age(info_dict.get("屋齡"))
    public_ratio = parse_percent(info_dict.get("公設比"))
    manage_fee = parse_currency_amount(info_dict.get("管理費"))
    has_lease = parse_boolean(info_dict.get("帶租約"))
    balconies = parse_int_count(info_dict.get("陽台"))

    # 8. 結構化地址組裝與地區名稱對齊
    region_str = str(address_info.get("region") or (summary.region_name if summary else "") or "").strip()
    section_str = str(address_info.get("section") or (summary.section_name if summary else "") or "").strip()
    street_str = str(address_info.get("street") or (summary.street if summary else "") or "").strip()
    addr_str = str(address_info.get("addr") or "").strip()
    num_str = f"{address_info.get('addr_number')}號" if address_info.get("addr_number") else ""
    full_address = f"{region_str}{section_str}{street_str}{addr_str}{num_str}"
    if not full_address and summary and summary.address:
        full_address = summary.address

    # 9. 社區資訊與封面圖注入 (清單 API 為權威 SSOT)
    comm_id = summary.community_id if summary and summary.community_id else clean_optional_str(data.get("community_id"))
    comm_name = summary.community_name if summary and summary.community_name else clean_optional_str(data.get("community_name"))
    cover_image = summary.cover_image_url if summary and summary.cover_image_url else clean_optional_str(data.get("photo_src"))

    raw_id = str(data.get("id") or (summary.external_house_id if summary else "") or "").strip().upper()
    canonical_id = raw_id if raw_id.startswith("S") else f"S{raw_id}"

    title = str(base_info.get("title") or (summary.title if summary else "") or "").strip()

    return NormalizedSalePropertyDetail(
        external_house_id=canonical_id,
        title=title,
        price_wan=price_wan,
        unit_price_wan=unit_price,
        total_area_pin=total_area,
        main_area_pin=main_area,
        auxiliary_area_pin=aux_area,
        common_area_pin=common_area,
        land_area_pin=land_area,
        parking_area_pin=parking_area,
        floor_current=floor_curr if floor_curr is not None else (summary.floor_current if summary else None),
        floor_total=floor_tot if floor_tot is not None else (summary.floor_total if summary else None),
        rooms=rooms if rooms is not None else (summary.rooms if summary else None),
        living_rooms=living if living is not None else (summary.living_rooms if summary else None),
        bathrooms=baths if baths is not None else (summary.bathrooms if summary else None),
        balconies=balconies,
        building_age_years=building_age,
        public_ratio_pct=public_ratio,
        management_fee_monthly=manage_fee,
        has_lease=has_lease,
        building_type=clean_optional_str(data.get("kindStr") or (summary.building_type if summary else None)),
        building_structure=clean_optional_str(info_dict.get("型態")),
        orientation=clean_optional_str(info_dict.get("朝向")),
        purpose=clean_optional_str(info_dict.get("用途")),
        current_state=clean_optional_str(info_dict.get("現況")),
        parking_desc=clean_optional_str(base_info.get("parking")),
        region_name=clean_optional_str(region_str),
        section_name=clean_optional_str(section_str),
        street=clean_optional_str(street_str),
        address=clean_optional_str(full_address),
        coordinates=GeoPoint(lat=lat, lng=lng) if lat is not None and lng is not None else None,
        community_id=comm_id,
        community_name=comm_name,
        cover_image_url=cover_image,
    )

