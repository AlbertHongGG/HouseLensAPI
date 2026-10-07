"""HouseLensAPI - 永慶房屋模組內部數據正規化引擎 (Yungching Self-Normalization Engine)

模組內部專用：負責將永慶房屋特化封包之各類字串、雜質、格局、樓層徹底清洗為標準強型別數值。
主程式絕不依賴此模組，確保永慶平台的所有封包特性皆被完整封裝於外掛內部。
"""

import re
from typing import Any, List, Optional, Tuple


def clean_str(val: Any) -> Optional[str]:
    """清洗字串，空值、空字串或全空白傳回 None"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_float(val: Any) -> Optional[float]:
    """安全解析浮點數 (去除文字單位干擾，如 '8.0年', '91.4萬/坪', '43.22')"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r"[^\d.]", "", str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def parse_int(val: Any) -> Optional[int]:
    """安全解析整數 (去除千分位逗號與非數字符號)"""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    try:
        cleaned = re.sub(r"[^\d]", "", str(val))
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def normalize_region_name(raw_region: Optional[str]) -> Optional[str]:
    """正規化縣市名稱，統一將「臺」替換為「台」"""
    if not raw_region:
        return None
    norm = str(raw_region).strip().replace("臺", "台")
    return norm if norm else None


def parse_layout(layout_str: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
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


def parse_floor(floor_str: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """解析樓層字串 (例如: '4樓/11樓', 'B1樓/12樓', '地下1樓/7樓') 傳回 (current_floor, total_floor)"""
    if not floor_str or not isinstance(floor_str, str):
        return None, None

    curr_floor = None
    tot_floor = None

    parts = floor_str.split("/")
    if len(parts) >= 1:
        c_part = parts[0].strip()
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


def parse_car_area(car_str: Optional[str]) -> Optional[float]:
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


def extract_street(address: Optional[str]) -> Optional[str]:
    """從完整地址字串中萃取路街名稱"""
    if not address or not isinstance(address, str):
        return None
    match = re.search(r"(?:市|縣)?(?:.+?區|.+?鄉|.+?鎮)?(.+?(?:路|街|大道|巷))", address)
    if match:
        return match.group(1).strip()
    return None


def is_whole_building(type_str: Optional[str]) -> bool:
    """判斷建物型態是否為整棟銷售 (透天、別墅、整棟)"""
    if not type_str:
        return False
    return any(k in str(type_str) for k in ("透天", "別墅", "整棟"))


def parse_facilities(val: Any) -> List[str]:
    """從公設描述字串中正則萃取清潔的公共設施清單"""
    if not val or not isinstance(val, str):
        return []

    text = val.strip()
    bracket_match = re.search(r"[（\(](.*?)[）\)]", text)
    if bracket_match:
        content = bracket_match.group(1)
        items = re.split(r"[、,，\s/]+", content)
        cleaned = []
        for it in items:
            it = re.sub(r"等.*$", "", it).strip()
            it = re.sub(r"\.+$", "", it).strip()
            if it and len(it) > 1 and it not in cleaned:
                cleaned.append(it)
        if cleaned:
            return cleaned

    raw_items = re.split(r"[、,，\s]+", text)
    result = []
    for it in raw_items:
        it = it.strip()
        if it and len(it) > 1 and it not in ("公設", "公共設備", "設施", "完善", "無") and it not in result:
            result.append(it)
    return result
