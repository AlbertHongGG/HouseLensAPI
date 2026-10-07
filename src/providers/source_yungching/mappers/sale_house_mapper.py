"""HouseLensAPI - 永慶房屋中古屋資料模型正規化轉換器 (Yungching Sale House Mapper)

嚴格落實兩層式權威單一事實來源 (Two-Tier SSOT)：
- 清單 API (/v2/SearchHouse)：專責提取 8 大最小必要刊登資訊 (NormalizedSaleListing)，
  提供 property_listings 之 listing_price_wan 與快篩屬性。
- 詳情 API (/v2/houseDetail/Base)：深層物理實體規格 100% 在此取得 (NormalizedSalePropertyDetail)，
  包括實體總價 price_wan、每坪單價 unit_price_wan、產權五大面積拆解、
  樓層格局、關聯社區、大圖相簿與官方展示網址。
- 客觀無資料：公設比、帶租約、現況等欄位 100% 乾淨傳入 None (入庫為 SQL NULL)。
所有數據清洗與正則拆解邏輯統一委派至 source_yungching.normalizers。
"""

import re
from typing import Any, Dict, Optional, Union

from src.domain.common import GeoPoint
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_yungching.mappers.photos_dto import (
    SourceYungchingSalePhotosDTO,
    normalize_yungching_image_url,
)
from src.providers.source_yungching.normalizers import (
    clean_str,
    extract_street,
    is_whole_building,
    normalize_region_name,
    parse_car_area,
    parse_floor,
    parse_float,
    parse_int,
    parse_layout,
)


def map_yungching_sale_listing(
    raw_item: Dict[str, Any], query_region: Optional[str] = None
) -> NormalizedSaleListing:
    """將永慶房屋清單項目轉換為標準 NormalizedSaleListing (最小必要刊登資訊)

    權威歸屬：
    - external_house_id: 100% 取自清單 CaseID (GUID)
    - title: 100% 取自清單 CaseName
    - price_wan: 100% 取自清單 Price (刊登開價)
    - total_area_pin: 100% 取自清單 RegArea
    - cover_image_url: 100% 取自清單 Picture (升級 1200x900)
    - is_whole_building: 100% 依清單 CaseTypeName 判定
    """
    case_id = str(raw_item.get("CaseID") or "")
    title = str(raw_item.get("CaseName") or "").strip()
    price = parse_int(raw_item.get("Price")) or 0
    area = parse_float(raw_item.get("RegArea")) or 0.0
    age = parse_float(raw_item.get("BuildAge"))
    bld_type = clean_str(raw_item.get("CaseTypeName"))
    addr = str(raw_item.get("Address") or "").strip()

    # 格局快篩解析
    rooms, l_rooms, b_rooms = parse_layout(raw_item.get("LayOut"))

    # 地址切分縣市與行政區
    region = None
    section = ""
    street = None

    addr_match = re.search(r"^(.{2,3}[市縣])(.{2,3}[區鄉鎮市])(.*)$", addr)
    if addr_match:
        region = normalize_region_name(addr_match.group(1))
        section = addr_match.group(2).strip()
        street = extract_street(addr)
    else:
        region = normalize_region_name(query_region or "台北市")

    cover = normalize_yungching_image_url(raw_item.get("Picture"))

    return NormalizedSaleListing(
        provider_id="yungching",
        external_house_id=case_id,
        title=title,
        price_wan=price,
        unit_price_wan=None,
        total_area_pin=area,
        floor_current=None,
        floor_total=None,
        rooms=rooms,
        living_rooms=l_rooms,
        bathrooms=b_rooms,
        building_age_years=age,
        building_type=bld_type,
        is_whole_building=is_whole_building(bld_type),
        region_name=region or "台北市",
        section_name=section,
        street=street,
        address=addr if addr else None,
        external_community_id=None,
        community_name=None,
        has_parking=bool(raw_item.get("ParkingSpace") and raw_item.get("ParkingSpace") != "無車位"),
        cover_image_url=cover,
        url=f"https://buy.yungching.com.tw/house/{case_id}" if case_id else None,
    )


def map_yungching_sale_detail(
    raw_detail: Union[Dict[str, Any], NormalizedSaleListing],
    summary: Optional[Union[NormalizedSaleListing, Dict[str, Any]]] = None,
    *,
    listing: Optional[NormalizedSaleListing] = None,
) -> NormalizedSalePropertyDetail:
    """將永慶房屋封包組裝為強型別 NormalizedSalePropertyDetail

    自足架構 (Self-Contained)：
    - 支援 100% 直接自 raw_detail 解析所有物理實體規格，不強制需要 summary 物件。
    - 若外部有提供 summary，可用於補足缺漏之刊登元數據。
    - 實體總價 price_wan 與每坪單價 unit_price_wan 100% 來自詳情 API。
    - 產權五大面積拆解、精確樓層格局、關聯社區、大圖相簿 100% 來自詳情 API。
    - 公設比、帶租約、現況等客觀無資料欄位 100% 傳入 None (入庫為 SQL NULL)。
    """
    # 參數容錯與解構：支援 (raw_detail, summary) 與相容 (listing, raw_detail) 兩種傳參方式
    actual_detail_raw: Dict[str, Any]
    actual_summary: Optional[NormalizedSaleListing] = listing

    if isinstance(raw_detail, NormalizedSaleListing):
        actual_summary = raw_detail
        actual_detail_raw = summary if isinstance(summary, dict) else {}
    elif isinstance(raw_detail, dict):
        actual_detail_raw = raw_detail
        if isinstance(summary, NormalizedSaleListing):
            actual_summary = summary
    else:
        actual_detail_raw = {}

    detail_data = actual_detail_raw.get("Data") if isinstance(actual_detail_raw.get("Data"), dict) else actual_detail_raw

    # 基礎識別身分 (100% 詳情優先，無則由 summary 補足)
    external_id = clean_str(detail_data.get("CaseID")) or (actual_summary.external_house_id if actual_summary else "")
    title = clean_str(detail_data.get("CaseName")) or (actual_summary.title if actual_summary else "")

    # --- 價格與單價：100% 來自詳情 API (使用者權威要求) ---
    price_wan = parse_int(detail_data.get("Price")) or (actual_summary.price_wan if actual_summary else 0)
    unit_price = parse_float(detail_data.get("UnitPrice"))

    # --- 產權五大面積純浮點數拆解 (100% 來自詳情 RegisterInfo) ---
    reg_info = detail_data.get("RegisterInfo") or {}
    total_area = parse_float(reg_info.get("RegArea")) or (actual_summary.total_area_pin if actual_summary else 0.0)
    main_area = parse_float(reg_info.get("MainArea"))
    auxi_area = parse_float(reg_info.get("TotalAuxiArea"))
    common_area = parse_float(reg_info.get("PublicArea"))
    land_area = parse_float(reg_info.get("LandPin"))
    parking_area = parse_car_area(reg_info.get("CarArea"))

    # --- 建築硬體與格局 (100% 來自詳情 HouseInfo) ---
    house_info = detail_data.get("HouseInfo") or {}
    curr_floor, tot_floor = parse_floor(house_info.get("Floor"))
    rooms, l_rooms, b_rooms = parse_layout(house_info.get("LayOut"))
    if rooms is None and actual_summary:
        rooms = actual_summary.rooms
    if l_rooms is None and actual_summary:
        l_rooms = actual_summary.living_rooms
    if b_rooms is None and actual_summary:
        b_rooms = actual_summary.bathrooms

    # 陽台數判定
    auxi_content = str(reg_info.get("TotalAuxiAreaContent") or "")
    balconies = 1 if "陽台" in auxi_content and auxi_area and auxi_area > 0 else None

    building_age = parse_float(house_info.get("Age")) or (actual_summary.building_age_years if actual_summary else None)
    building_type = clean_str(house_info.get("Type")) or (actual_summary.building_type if actual_summary else None)
    purpose = clean_str(house_info.get("Purpose"))
    parking_desc = clean_str(house_info.get("ParkingSpace"))

    # 朝向清洗 (例如: '朝向北' -> '朝北')
    raw_dir = house_info.get("Direction")
    orientation = raw_dir.replace("朝向", "朝").strip() if raw_dir else None

    # 整棟銷售標記
    is_whole = is_whole_building(building_type) if building_type else (actual_summary.is_whole_building if actual_summary else False)

    # --- 建物與社區規劃 (100% 來自詳情 BuildingInfo) ---
    bld_info = detail_data.get("BuildingInfo") or {}
    community_id = clean_str(bld_info.get("CommunityID"))
    community_name = clean_str(bld_info.get("BuildingName"))
    structure = clean_str(bld_info.get("Structure"))
    manage_fee = parse_int(bld_info.get("ManageExpense"))

    # --- 地理位置與座標 (100% 來自詳情 API) ---
    region_name = normalize_region_name(detail_data.get("County")) or (actual_summary.region_name if actual_summary else "台北市")
    section_name = clean_str(detail_data.get("District")) or (actual_summary.section_name if actual_summary else "")
    address = clean_str(detail_data.get("Address")) or (actual_summary.address if actual_summary else None)
    street = extract_street(address) or (actual_summary.street if actual_summary else None)

    lat = parse_float(detail_data.get("CoordinateY2"))
    lng = parse_float(detail_data.get("CoordinateX2"))
    coords = GeoPoint(lat=lat, lng=lng) if lat is not None and lng is not None else None

    # --- 相簿圖片與官方網址 (100% 來自詳情 API) ---
    photos_dto = SourceYungchingSalePhotosDTO(detail_data)
    image_urls = photos_dto.image_urls
    cover_image = photos_dto.cover_url or (actual_summary.cover_image_url if actual_summary else None)
    url = clean_str(detail_data.get("ShareLink")) or (
        f"https://buy.yungching.com.tw/house/{external_id}"
        if external_id
        else None
    )

    return NormalizedSalePropertyDetail(
        provider_id="yungching",
        external_house_id=external_id,
        title=title,
        price_wan=price_wan,
        unit_price_wan=unit_price,
        total_area_pin=total_area,
        main_area_pin=main_area,
        auxiliary_area_pin=auxi_area,
        common_area_pin=common_area,
        land_area_pin=land_area,
        parking_area_pin=parking_area,
        floor_current=curr_floor,
        floor_total=tot_floor,
        rooms=rooms,
        living_rooms=l_rooms,
        bathrooms=b_rooms,
        balconies=balconies,
        building_age_years=building_age,
        public_ratio_pct=None,
        management_fee_monthly=manage_fee,
        has_lease=None,
        building_type=building_type,
        structure=structure,
        is_whole_building=is_whole,
        orientation=orientation,
        purpose=purpose,
        current_state=None,
        parking_desc=parking_desc,
        region_name=region_name,
        section_name=section_name,
        street=street,
        address=address,
        coordinates=coords,
        external_community_id=community_id,
        community_name=community_name,
        cover_image_url=cover_image,
        image_urls=image_urls,
        url=url,
    )
