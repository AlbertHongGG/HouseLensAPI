"""HouseLensAPI - 信義房屋數值清洗與強型別轉換防腐層 (Sinyi Data Transformers)

純函數模組：負責將信義房屋手機端原始封包資料清洗為跨來源統一之領域規格。
嚴格遵循單一事實來源 (SSOT) 鐵律：
- 清單項目 (NormalizedSaleListing) 100% 自清單 API (/filterObject.php) 提取。
- 實體詳情 (NormalizedSalePropertyDetail) 100% 自詳情 API (/getObjectContent.php) 提取。
- 客觀無資料欄位 100% 純化為 None (SQL NULL)。
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.domain.common import GeoPoint
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)

logger = logging.getLogger(__name__)


def parse_float(val: Any) -> Optional[float]:
    """安全解析浮點數"""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f >= 0.0 else None
    except (ValueError, TypeError):
        return None


def parse_int(val: Any) -> Optional[int]:
    """安全解析純整數"""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        # 嘗試正則提取純數字
        m = re.search(r"\d+", str(val))
        return int(m.group()) if m else None


def parse_floor(val: Any) -> Optional[int]:
    """解析所在樓層 (支援地下室 B1 -> -1)"""
    if val is None:
        return None
    s = str(val).strip().upper()
    if not s:
        return None
    if s.startswith("B"):
        m = re.search(r"B(\d+)", s)
        return -int(m.group(1)) if m else -1
    m = re.search(r"(-?\d+)", s)
    return int(m.group(1)) if m else None


def parse_age(val: Any) -> Optional[float]:
    """解析屋齡純浮點數 (如 '0.0', '1.3年', '0.5年')"""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    m = re.search(r"([\d\.]+)", s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def parse_unit_price(price_item: Any, raw_uni_price: Any) -> Optional[float]:
    """解析每坪單價浮點數 (萬元/坪)

    詳情 API content.price_item 可能為 '87.90 萬/坪' 或 '本物件含車位，詳洽經紀人員'。
    content.rawUniPrice 可能為 '88.13 萬'。
    """
    if price_item:
        s = str(price_item).strip()
        m = re.search(r"([\d\.]+)\s*萬/坪", s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    if raw_uni_price:
        s = str(raw_uni_price).strip()
        m = re.search(r"([\d\.]+)", s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    return None


def parse_layout(layout_str: Any) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """解析格局文字 (如 '3房2廳2衛' 或 '1房1衛') 為 (房數, 廳數, 衛數)"""
    if not layout_str:
        return (None, None, None)
    s = str(layout_str).strip()

    rooms = None
    living_rooms = None
    bathrooms = None

    m_room = re.search(r"(\d+)\s*房", s)
    if m_room:
        rooms = int(m_room.group(1))

    m_hall = re.search(r"(\d+)\s*廳", s)
    if m_hall:
        living_rooms = int(m_hall.group(1))

    m_bath = re.search(r"(\d+)\s*衛", s)
    if m_bath:
        bathrooms = int(m_bath.group(1))

    return (rooms, living_rooms, bathrooms)


def parse_management_fee(fee_val: Any) -> Optional[int]:
    """解析每月管理費純整數 (元/月)

    如 '每月約 14,095 元(車位管理費另繳納 1,600 元 / 月繳)' 提取 14095。
    """
    if not fee_val:
        return None
    s = str(fee_val).strip()
    if not s or s in ("無", "暫無", "未提供"):
        return None

    # 提取第一個金額
    m = re.search(r"([\d,]+)\s*元", s)
    if m:
        digits = m.group(1).replace(",", "")
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def parse_address(address_val: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """台灣標準地址三級正則拆解 -> (縣市, 行政區, 路街)

    如 '台北市文山區木柵路二段' -> ('台北市', '文山區', '木柵路二段')
    """
    if not address_val:
        return (None, None, None)
    addr = str(address_val).strip()

    region = None
    section = None
    street = None

    # 1. 縣市
    m_reg = re.search(r"^([^市縣]+[市縣])", addr)
    if m_reg:
        region = m_reg.group(1).replace("臺", "台")
        addr_remain = addr[len(m_reg.group(1)) :]
    else:
        addr_remain = addr

    # 2. 行政區
    m_sec = re.search(r"^([^區鄉鎮市]+[區鄉鎮市])", addr_remain)
    if m_sec:
        section = m_sec.group(1)
        addr_remain = addr_remain[len(section) :]

    # 3. 路街段
    m_str = re.search(r"^([^路街道]+[路街道](?:[一二三四五六七八九十\d]+段)?)", addr_remain)
    if m_str:
        street = m_str.group(1)

    return (region, section, street)


def normalize_orientation(front_val: Any) -> Optional[str]:
    """房屋座向文字正規化 (如 '南' -> '朝南', '東南' -> '朝東南')"""
    if not front_val:
        return None
    s = str(front_val).strip()
    if not s or s in ("無", "不詳", "暫無"):
        return None
    if s.startswith("朝") or s.startswith("坐"):
        return s
    return f"朝{s}"


def parse_coordinates(lat_val: Any, lng_val: Any) -> Optional[GeoPoint]:
    """解析地理座標"""
    lat = parse_float(lat_val)
    lng = parse_float(lng_val)
    if lat is not None and lng is not None and 20.0 <= lat <= 27.0 and 118.0 <= lng <= 123.0:
        return GeoPoint(lat=lat, lng=lng)
    return None


def parse_image_urls(images: Any, layout_image: Any) -> List[str]:
    """解析相簿大圖清單與格局圖，並保證順序與去重"""
    urls: List[str] = []
    if isinstance(images, list):
        for img in images:
            if img and isinstance(img, str) and img.strip():
                clean_url = img.strip()
                if clean_url not in urls:
                    urls.append(clean_url)

    if layout_image and isinstance(layout_image, str) and layout_image.strip():
        layout_clean = layout_image.strip()
        if layout_clean not in urls:
            urls.append(layout_clean)

    return urls


def transform_sinyi_listing_item(obj: Dict[str, Any]) -> NormalizedSaleListing:
    """將清單 API (/filterObject.php) 的 object 元素轉換為標準刊登模型

    所有欄位 100% 來自清單 API，未提供者純化為 None。
    """
    house_no = str(obj.get("houseNo", "")).strip()
    name = str(obj.get("name", "")).strip()
    price = int(obj.get("price", 0))
    area_building = float(obj.get("areaBuilding", 0.0))

    floor_curr = parse_floor(obj.get("floor"))
    floor_tot = parse_int(obj.get("floors"))
    rooms, halls, baths = parse_layout(obj.get("layout") or obj.get("totalLayout"))
    age = parse_age(obj.get("age"))

    raw_addr = obj.get("address")
    region, section, street = parse_address(raw_addr)
    # 若地址未拆出縣市行政區，提供自衛預設
    region_val = region or "台北市"
    section_val = section or ""

    comm_id = str(obj.get("commId", "")).strip() or None
    cover_img = obj.get("largeImage") or obj.get("image") or None

    return NormalizedSaleListing(
        provider_id="sinyi",
        external_house_id=house_no,
        title=name,
        price_wan=price,
        unit_price_wan=None,  # 清單未提供結構化單價
        total_area_pin=area_building,
        floor_current=floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=halls,
        bathrooms=baths,
        building_age_years=age,
        building_type=None,  # 清單未提供建物型態
        is_whole_building=False,
        region_name=region_val,
        section_name=section_val,
        street=street,
        address=raw_addr,
        external_community_id=comm_id,
        community_name=None,  # 清單未提供社區名稱
        has_parking=bool(obj.get("isParking", False)),
        cover_image_url=cover_img,
        url=None,  # 清單未提供官方展示網址，固定為 None，由詳情提供
        raw_data=obj,
    )


def transform_sinyi_property_detail(content: Dict[str, Any]) -> NormalizedSalePropertyDetail:
    """將詳情 API (/getObjectContent.php) 的 content 字典轉換為完整實體規格模型

    所有規格 100% 來自詳情 API，客觀無數據者 100% 純化為 None (SQL NULL)。
    """
    house_no = str(content.get("houseNo", "")).strip()
    name = str(content.get("name", "")).strip()
    price = int(content.get("price", 0))
    unit_price = parse_unit_price(content.get("price_item"), content.get("rawUniPrice"))
    total_area = float(content.get("areaBuilding", 0.0))

    # 產權面積純浮點數拆解
    main_area = parse_float(content.get("mainBuilding"))
    ping_used = parse_float(content.get("pingUsed"))
    aux_area: Optional[float] = None
    balconies: Optional[int] = None
    if ping_used is not None and main_area is not None:
        diff = round(ping_used - main_area, 2)
        if diff > 0.0:
            aux_area = diff
            balconies = 1  # 陽台/附屬建物存在

    land_area = parse_float(content.get("areaLand"))

    # 格局與樓層
    rooms, halls, baths = parse_layout(content.get("layout") or content.get("totalLayout"))
    floor_curr = parse_floor(content.get("floor"))
    floor_tot = parse_int(content.get("floors"))
    age = parse_age(content.get("age"))

    # 管理費與型態
    mgmt_fee = parse_management_fee(content.get("monthlyFee"))
    b_type = content.get("type") or None
    is_whole = False
    if b_type:
        is_whole = any(k in b_type for k in ("透天", "別墅", "整棟"))

    orientation = normalize_orientation(content.get("houseFront"))
    parking_desc = content.get("parking") or None

    # 地址與經緯度
    raw_addr = content.get("address")
    region, section, street = parse_address(raw_addr)
    coords = parse_coordinates(content.get("latitude"), content.get("longitude"))

    # 社區關聯代碼與名稱
    comm_id = str(content.get("commId", "")).strip() or None
    comm_name = str(content.get("commName", "")).strip() or None

    # 高清圖庫與展示連結
    images = parse_image_urls(content.get("images"), content.get("layoutImage"))
    cover_img = images[0] if images else None
    share_url = content.get("shareURL") or None

    return NormalizedSalePropertyDetail(
        provider_id="sinyi",
        external_house_id=house_no,
        title=name,
        price_wan=price,
        unit_price_wan=unit_price,
        total_area_pin=total_area,
        # 產權面積純浮點數拆解
        main_area_pin=main_area,
        auxiliary_area_pin=aux_area,
        common_area_pin=None,  # 客觀無資料 -> 100% SQL NULL
        land_area_pin=land_area,
        parking_area_pin=None,  # 客觀無資料 -> 100% SQL NULL
        # 建築物理規格 (純數值)
        floor_current=floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=halls,
        bathrooms=baths,
        balconies=balconies,
        building_age_years=age,
        public_ratio_pct=None,  # 客觀無資料 -> 100% SQL NULL
        management_fee_monthly=mgmt_fee,
        has_lease=None,  # 客觀無資料 -> 100% SQL NULL
        # 構造與現況描述
        building_type=b_type,
        structure=None,  # 客觀無資料 -> 100% SQL NULL
        is_whole_building=is_whole,
        orientation=orientation,
        purpose=None,  # 客觀無資料 -> 100% SQL NULL
        current_state=None,  # 客觀無資料 -> 100% SQL NULL
        parking_desc=parking_desc,
        # 地理位置與結構化資訊
        region_name=region,
        section_name=section,
        street=street,
        address=raw_addr,
        coordinates=coords,
        external_community_id=comm_id,
        community_name=comm_name,
        cover_image_url=cover_img,
        image_urls=images,
        url=share_url,
    )
