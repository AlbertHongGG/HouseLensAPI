"""HouseLensAPI - 信義房屋模組內部數據正規化引擎 (Sinyi Self-Normalization Engine)

模組內部專用純函數庫：負責將信義房屋原始封包之字串、雜質、格局、樓層、公設比等
徹底清洗為跨來源統一之標準強型別數值。
主程式與其他 Provider 絕不依賴此模組，確保信義平台特性完整封裝。
"""

import logging
import re
from typing import Any, List, Optional, Tuple

from src.domain.common import GeoPoint

logger = logging.getLogger(__name__)


def clean_str(val: Any) -> Optional[str]:
    """清洗字串，空值、空字串或全空白傳回 None"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_float(val: Any) -> Optional[float]:
    """安全解析浮點數 (去除文字單位干擾)"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if f >= 0.0 else None
    s = str(val).strip()
    if not s:
        return None
    try:
        f = float(s)
        return f if f >= 0.0 else None
    except ValueError:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            try:
                f = float(m.group(1))
                return f if f >= 0.0 else None
            except ValueError:
                return None
    return None


def parse_int(val: Any) -> Optional[int]:
    """安全解析純整數 (去除千分位逗號與非數字符號)"""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    s = str(val).strip()
    if not s:
        return None
    try:
        cleaned = re.sub(r"[^\d]", "", s)
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


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
    """解析地理座標並驗證台灣合理經緯度邊界"""
    lat = parse_float(lat_val)
    lng = parse_float(lng_val)
    if lat is not None and lng is not None and 20.0 <= lat <= 27.0 and 118.0 <= lng <= 123.0:
        return GeoPoint(lat=lat, lng=lng)
    return None


def parse_public_ratio(val: Any) -> Optional[float]:
    """解析公設比百分比字串 (例如 '32.00%~36.00%' -> 32.0, '35%' -> 35.0)"""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        try:
            return float(m.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_facilities(val: Any) -> List[str]:
    """將公設描述字串以逗號或標點切分為清單 (例如 'SPA,花園,室內泳池,健身房')"""
    if not val:
        return []
    s = str(val).strip()
    if not s:
        return []
    parts = re.split(r"[,，、\s]+", s)
    return [p.strip() for p in parts if p.strip()]


def parse_image_urls(images: Any, layout_image: Any = None) -> List[str]:
    """解析並過濾相簿大圖清單與格局圖，保證順序與去重"""
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
