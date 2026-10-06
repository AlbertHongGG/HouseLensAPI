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
    floor_curr, floor_tot, is_whole_building = parse_floor(item.get("floor"))
    if floor_tot is None and item.get("all_floor"):
        _, parsed_tot, _ = parse_floor(item.get("all_floor"))
        floor_tot = parsed_tot or parse_int_count(item.get("all_floor"))

    rooms, living, baths = parse_layout(item.get("layout_str"))

    # 4. 客觀外部社區代碼與名稱精確解析 (杜絕路名偽裝社區)
    comm_info = item.get("community_info")
    comm_name: Optional[str] = None
    ext_comm_id: Optional[str] = None

    if isinstance(comm_info, dict):
        raw_cname = comm_info.get("community_name")
        if raw_cname and str(raw_cname).strip():
            comm_name = str(raw_cname).strip()
        raw_cid = comm_info.get("community_id")
        if raw_cid and str(raw_cid).strip() not in ("0", ""):
            ext_comm_id = str(raw_cid).strip()

    if not ext_comm_id:
        top_cid = item.get("community_id")
        if top_cid and str(top_cid).strip() not in ("0", ""):
            ext_comm_id = str(top_cid).strip()

    raw_hid = str(item.get("houseid") or "").strip().upper()
    canonical_hid = raw_hid if raw_hid.startswith("S") else f"S{raw_hid}"

    return NormalizedSaleListing(
        provider_id="591",
        external_house_id=canonical_hid,
        title=str(item.get("title") or "").strip(),
        price_wan=price_wan,
        unit_price_wan=unit_price_wan,
        total_area_pin=total_area_pin,
        floor_current=None if is_whole_building else floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=living,
        bathrooms=baths,
        building_age_years=None,  # 591 清單端點無屋齡欄位，詳情端點補齊
        building_type=clean_optional_str(item.get("kindStr")),
        is_whole_building=is_whole_building,
        region_name=str(item.get("region") or "").strip(),
        section_name=str(item.get("section") or "").strip(),
        street=clean_optional_str(item.get("street_name")),
        address=clean_optional_str(item.get("address")),
        external_community_id=clean_optional_str(ext_comm_id),
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
    floor_curr, floor_tot, is_whole_building = parse_floor(info_dict.get("樓層"))
    if not is_whole_building and summary and summary.is_whole_building:
        is_whole_building = True
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

    # 5. 總登記坪數浮點數 (100% 詳情 API 單一事實來源)
    total_area = parse_pin(base_info.get("area")) or 0.0

    # 6. 金額與單價 (100% 詳情 API 單一事實來源)
    price_wan = parse_price_wan(base_info.get("price"))
    unit_price = parse_unit_price(base_info.get("unitPrice"))

    # 7. 屋齡、公設比、管理費數值化
    building_age = Source591AgeMapper.parse_building_age(info_dict.get("屋齡"))
    public_ratio = parse_percent(info_dict.get("公設比"))
    manage_fee = parse_currency_amount(info_dict.get("管理費"))
    has_lease = parse_boolean(info_dict.get("帶租約"))
    balconies = parse_int_count(info_dict.get("陽台"))

    # 8. 結構化地址組裝 (詳情備用語意)
    raw_region = clean_optional_str(address_info.get("region"))
    raw_section = clean_optional_str(address_info.get("section"))
    raw_street = clean_optional_str(address_info.get("street"))
    addr_str = str(address_info.get("addr") or "").strip()
    num_str = f"{address_info.get('addr_number')}號" if address_info.get("addr_number") else ""
    full_address = f"{raw_region or ''}{raw_section or ''}{raw_street or ''}{addr_str}{num_str}"

    # --- 第一層：身分與地理空間標識 (100% 統一自清單 API summary) ---
    raw_id = str(data.get("id") or "").strip().upper()
    canonical_id = raw_id if raw_id.startswith("S") else f"S{raw_id}"

    ext_house_id = summary.external_house_id if summary else canonical_id
    title = summary.title if summary else str(base_info.get("title") or "").strip()
    region_name = summary.region_name if summary else raw_region
    section_name = summary.section_name if summary else raw_section
    street_name = summary.street if summary else raw_street
    address_str = summary.address if summary else clean_optional_str(full_address)
    ext_comm_id = summary.external_community_id if summary else clean_optional_str(data.get("community_id"))
    comm_name = summary.community_name if summary else clean_optional_str(data.get("community_name"))
    cover_image = summary.cover_image_url if summary else clean_optional_str(data.get("photo_src"))

    return NormalizedSalePropertyDetail(
        # --- 第一層：身分與地理空間標識 ---
        provider_id=summary.provider_id if summary else "591",
        external_house_id=ext_house_id,
        title=title,
        region_name=region_name,
        section_name=section_name,
        street=street_name,
        address=address_str,
        external_community_id=ext_comm_id,
        community_name=comm_name,
        cover_image_url=cover_image,
        # --- 第二層：深層建築、硬體規格與時程層 (100% 詳情 API 唯一來源) ---
        price_wan=price_wan,
        unit_price_wan=unit_price,
        total_area_pin=total_area,
        main_area_pin=main_area,
        auxiliary_area_pin=aux_area,
        common_area_pin=common_area,
        land_area_pin=land_area,
        parking_area_pin=parking_area,
        is_whole_building=is_whole_building,
        floor_current=None if is_whole_building else floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=living,
        bathrooms=baths,
        balconies=balconies,
        building_age_years=building_age,
        public_ratio_pct=public_ratio,
        management_fee_monthly=manage_fee,
        has_lease=has_lease,
        building_type=clean_optional_str(data.get("kindStr")),
        structure=clean_optional_str(info_dict.get("型態")),
        orientation=clean_optional_str(info_dict.get("朝向")),
        purpose=clean_optional_str(info_dict.get("用途")),
        current_state=clean_optional_str(info_dict.get("現況")),
        parking_desc=clean_optional_str(base_info.get("parking")),
        coordinates=GeoPoint(lat=lat, lng=lng) if lat is not None and lng is not None else None,
    )

