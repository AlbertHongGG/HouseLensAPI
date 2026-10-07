"""HouseLensAPI - 永慶房屋中古屋資料模型正規化轉換器 (Yungching Sale House Mapper)

嚴格落實兩層式權威單一事實來源 (Two-Tier SSOT)：
- 清單 API (/v2/SearchHouse)：專責提取 8 大最小必要刊登資訊 (NormalizedSaleListing)，
  提供 property_listings 之 listing_price_wan 與快篩屬性。
- 詳情 API (/v2/houseDetail/Base)：深層物理實體規格 100% 在此取得 (NormalizedSalePropertyDetail)，
  包括實體總價 price_wan、每坪單價 unit_price_wan、產權五大面積拆解、
  樓層格局、關聯社區、大圖相簿與官方展示網址。
- 客觀無資料：公設比、帶租約、現況等欄位 100% 乾淨傳入 None (入庫為 SQL NULL)。
"""

import re
from typing import Any, Dict, Optional, Tuple

from src.domain.common import GeoPoint
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_yungching.mappers.photos_dto import (
    SourceYungchingSalePhotosDTO,
    normalize_yungching_image_url,
)


def _clean_str(val: Any) -> Optional[str]:
    """清洗字串，空值或全空白傳回 None"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _parse_float(val: Any) -> Optional[float]:
    """安全解析浮點數"""
    if val is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _parse_int(val: Any) -> Optional[int]:
    """安全解析整數 (去除千分位逗號與非數字符號)"""
    if val is None:
        return None
    try:
        cleaned = re.sub(r"[^\d]", "", str(val))
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _normalize_region_name(raw_region: Optional[str]) -> Optional[str]:
    """正規化縣市名稱，統一將「臺」替換為「台」"""
    if not raw_region:
        return None
    norm = raw_region.strip().replace("臺", "台")
    return norm if norm else None


def _parse_layout(layout_str: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """解析格局字串 (例如: '3房(室)2廳2衛', '2房(室)1廳1.5衛') 傳回 (rooms, living_rooms, bathrooms)"""
    if not layout_str or not isinstance(layout_str, str):
        return None, None, None

    rooms = None
    living_rooms = None
    bathrooms = None

    # 房數
    r_match = re.search(r"(\d+)\s*房", layout_str)
    if r_match:
        rooms = int(r_match.group(1))

    # 廳數
    l_match = re.search(r"(\d+)\s*廳", layout_str)
    if l_match:
        living_rooms = int(l_match.group(1))

    # 衛數 (以整數為主)
    b_match = re.search(r"(\d+)(?:\.\d+)?\s*衛", layout_str)
    if b_match:
        bathrooms = int(b_match.group(1))

    return rooms, living_rooms, bathrooms


def _parse_floor(floor_str: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """解析樓層字串 (例如: '4樓/11樓', 'B1樓/12樓', '地下1樓/7樓') 傳回 (current_floor, total_floor)"""
    if not floor_str or not isinstance(floor_str, str):
        return None, None

    curr_floor = None
    tot_floor = None

    # 比對: 所在樓 / 總樓
    parts = floor_str.split("/")
    if len(parts) >= 1:
        c_part = parts[0].strip()
        # 判斷地下室
        if "B" in c_part.upper() or "地下" in c_part:
            digits = re.findall(r"\d+", c_part)
            if digits:
                curr_floor = -int(digits[0])
        else:
            digits = re.findall(r"\d+", c_part)
            if digits:
                curr_floor = int(digits[0])

    if len(parts) >= 2:
        t_part = parts[1].strip()
        digits = re.findall(r"\d+", t_part)
        if digits:
            tot_floor = int(digits[0])

    return curr_floor, tot_floor


def _parse_car_area(car_str: Optional[str]) -> Optional[float]:
    """從車位面積字串萃取純坪數 (例如: '(含車位3.92坪)' -> 3.92)"""
    if not car_str or not isinstance(car_str, str):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*坪", car_str)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def _extract_street(address: Optional[str]) -> Optional[str]:
    """從完整地址字串中萃取路街名稱"""
    if not address or not isinstance(address, str):
        return None
    # 比對縣市與行政區之後的路/街/大道/巷
    match = re.search(r"(?:市|縣)?(?:.+?區|.+?鄉|.+?鎮)?(.+?(?:路|街|大道|巷))", address)
    if match:
        return match.group(1).strip()
    return None


def _is_whole_building(type_str: Optional[str]) -> bool:
    """判斷建物型態是否為整棟銷售 (透天、別墅、整棟)"""
    if not type_str:
        return False
    return any(k in type_str for k in ("透天", "別墅", "整棟"))


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
    price = _parse_int(raw_item.get("Price")) or 0
    area = _parse_float(raw_item.get("RegArea")) or 0.0
    age = _parse_float(raw_item.get("BuildAge"))
    bld_type = _clean_str(raw_item.get("CaseTypeName"))
    addr = str(raw_item.get("Address") or "").strip()

    # 格局快篩解析
    rooms, l_rooms, b_rooms = _parse_layout(raw_item.get("LayOut"))

    # 地址切分縣市與行政區
    region = None
    section = ""
    street = None

    addr_match = re.search(r"^(.{2,3}[市縣])(.{2,3}[區鄉鎮市])(.*)$", addr)
    if addr_match:
        region = _normalize_region_name(addr_match.group(1))
        section = addr_match.group(2).strip()
        street = _extract_street(addr)
    else:
        region = _normalize_region_name(query_region or "台北市")

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
        is_whole_building=_is_whole_building(bld_type),
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
    listing: NormalizedSaleListing,
    raw_detail: Dict[str, Any],
) -> NormalizedSalePropertyDetail:
    """將永慶房屋封包組裝為強型別 NormalizedSalePropertyDetail

    職責邊界：
    - 基礎刊登身分來自 listing。
    - 實體總價 price_wan 與每坪單價 unit_price_wan 100% 來自詳情 API。
    - 產權五大面積拆解、精確樓層格局、關聯社區、大圖相簿 100% 來自詳情 API。
    - 公設比、帶租約、現況等客觀無資料欄位 100% 傳入 None (入庫為 SQL NULL)。
    """
    detail_data = raw_detail.get("Data") if isinstance(raw_detail.get("Data"), dict) else raw_detail

    # --- 價格與單價：100% 來自詳情 API (使用者權威要求) ---
    price_wan = _parse_int(detail_data.get("Price")) or listing.price_wan
    unit_price = _parse_float(detail_data.get("UnitPrice"))

    # --- 產權五大面積純浮點數拆解 (100% 來自詳情 RegisterInfo) ---
    reg_info = detail_data.get("RegisterInfo") or {}
    total_area = _parse_float(reg_info.get("RegArea")) or listing.total_area_pin
    main_area = _parse_float(reg_info.get("MainArea"))
    auxi_area = _parse_float(reg_info.get("TotalAuxiArea"))
    common_area = _parse_float(reg_info.get("PublicArea"))
    land_area = _parse_float(reg_info.get("LandPin"))
    parking_area = _parse_car_area(reg_info.get("CarArea"))

    # --- 建築硬體與格局 (100% 來自詳情 HouseInfo) ---
    house_info = detail_data.get("HouseInfo") or {}
    curr_floor, tot_floor = _parse_floor(house_info.get("Floor"))
    rooms, l_rooms, b_rooms = _parse_layout(house_info.get("LayOut"))
    if rooms is None:
        rooms = listing.rooms
    if l_rooms is None:
        l_rooms = listing.living_rooms
    if b_rooms is None:
        b_rooms = listing.bathrooms

    # 陽台數判定
    auxi_content = str(reg_info.get("TotalAuxiAreaContent") or "")
    balconies = 1 if "陽台" in auxi_content and auxi_area and auxi_area > 0 else None

    building_age = _parse_float(house_info.get("Age")) or listing.building_age_years
    building_type = _clean_str(house_info.get("Type")) or listing.building_type
    purpose = _clean_str(house_info.get("Purpose"))
    parking_desc = _clean_str(house_info.get("ParkingSpace"))

    # 朝向清洗 (例如: '朝向北' -> '朝北')
    raw_dir = house_info.get("Direction")
    orientation = raw_dir.replace("朝向", "朝").strip() if raw_dir else None

    # --- 建物與社區規劃 (100% 來自詳情 BuildingInfo) ---
    bld_info = detail_data.get("BuildingInfo") or {}
    community_id = _clean_str(bld_info.get("CommunityID"))
    community_name = _clean_str(bld_info.get("BuildingName"))
    structure = _clean_str(bld_info.get("Structure"))
    manage_fee = _parse_int(bld_info.get("ManageExpense"))

    # --- 地理位置與座標 (100% 來自詳情 API) ---
    region_name = _normalize_region_name(detail_data.get("County")) or listing.region_name
    section_name = _clean_str(detail_data.get("District")) or listing.section_name
    address = _clean_str(detail_data.get("Address")) or listing.address
    street = _extract_street(address) or listing.street

    lat = _parse_float(detail_data.get("CoordinateY2"))
    lng = _parse_float(detail_data.get("CoordinateX2"))
    coords = GeoPoint(lat=lat, lng=lng) if lat is not None and lng is not None else None

    # --- 相簿圖片與官方網址 (100% 來自詳情 API) ---
    photos_dto = SourceYungchingSalePhotosDTO(detail_data)
    image_urls = photos_dto.image_urls
    cover_image = photos_dto.cover_url or listing.cover_image_url
    url = _clean_str(detail_data.get("ShareLink")) or (
        f"https://buy.yungching.com.tw/house/{listing.external_house_id}"
        if listing.external_house_id
        else None
    )

    return NormalizedSalePropertyDetail(
        provider_id=listing.provider_id,
        external_house_id=listing.external_house_id,
        title=listing.title,
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
        is_whole_building=listing.is_whole_building,
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
