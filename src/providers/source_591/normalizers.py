"""HouseLensAPI - 591 模組內部數據正規化引擎 (591 Self-Normalization Engine)

模組內部專用：負責將 591 特化封包之各類字串、雜質、平台代碼徹底清洗為標準強型別數值。
主程式絕不依賴此模組，確保 591 平台的所有特性皆被完美封裝於外掛內部。
"""

import re
from typing import Any, Optional, Tuple


def parse_price_wan(raw: Any) -> int:
    """解析萬元總價純整數 (例如: 5258, "5,258萬元", "5258萬")"""
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)

    clean_str = str(raw).replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if match:
        try:
            return int(float(match.group(1)))
        except (ValueError, TypeError):
            return 0
    return 0


def parse_unit_price(raw: Any) -> Optional[float]:
    """解析萬元每坪單價浮點數 (例如: "132.2萬/坪", 132.2)"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    clean_str = str(raw).replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_pin(raw: Any) -> Optional[float]:
    """解析坪數浮點數 (例如: "46.29坪", 46.29, "23.10")"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    clean_str = str(raw).replace(",", "").replace("坪", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_floor(raw: Any) -> Tuple[Optional[int], Optional[int]]:
    """解析樓層為 (所在樓層純整數, 總樓層純整數)。

    支援格式:
        "2F/24F" -> (2, 24)
        "2樓/共24樓" -> (2, 24)
        "B1/12F" -> (-1, 12)
        "頂樓" / "整棟" -> (None, None)
        2 -> (2, None)
    """
    if raw is None:
        return (None, None)

    if isinstance(raw, int):
        return (raw, None)

    clean_str = str(raw).strip()
    if not clean_str:
        return (None, None)

    curr_floor: Optional[int] = None
    total_floor: Optional[int] = None

    if "/" in clean_str:
        parts = clean_str.split("/")
        curr_part = parts[0].strip()
        total_part = parts[1].strip()

        # 解析所在樓層
        curr_floor = _parse_single_floor(curr_part)
        total_floor = _parse_single_floor(total_part)
    else:
        curr_floor = _parse_single_floor(clean_str)

    return (curr_floor, total_floor)


def _parse_single_floor(s: str) -> Optional[int]:
    """輔助解析單一樓層字串 (支援地下室 B1 -> -1)"""
    if not s:
        return None
    s = s.upper().replace("F", "").replace("樓", "").replace("共", "").strip()
    if s.startswith("B"):
        b_num = s.replace("B", "").strip()
        if b_num.isdigit():
            return -int(b_num)
    if s.isdigit():
        return int(s)
    # 支援負數 "-1"
    if s.startswith("-") and s[1:].isdigit():
        return int(s)
    return None


def parse_layout(raw: Any) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """解析格局為 (房數, 廳數, 衛數) 純整數元組。

    支援格式:
        "3房2廳2衛" -> (3, 2, 2)
        "3房2廳" -> (3, 2, None)
        "1房1衛" -> (1, None, 1)
        "開放式格局" -> (0, 1, 1)
    """
    if not raw:
        return (None, None, None)

    s = str(raw).strip()
    if not s:
        return (None, None, None)

    rooms = None
    living = None
    baths = None

    m_room = re.search(r"(\d+)\s*房", s)
    if m_room:
        rooms = int(m_room.group(1))

    m_living = re.search(r"(\d+)\s*廳", s)
    if m_living:
        living = int(m_living.group(1))

    m_bath = re.search(r"(\d+)\s*衛", s)
    if m_bath:
        baths = int(m_bath.group(1))

    return (rooms, living, baths)


def parse_percent(raw: Any) -> Optional[float]:
    """解析百分比純浮點數 (例如: "30%", "34.5%", 30.0 -> 30.0)"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    clean_str = str(raw).replace("%", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", clean_str)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_currency_amount(raw: Any) -> Optional[int]:
    """解析純整數金額 (例如: "4200元/月", "4200元", 4200 -> 4200)"""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)

    clean_str = str(raw).replace(",", "").strip()
    match = re.search(r"(\d+)", clean_str)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_int_count(raw: Any) -> Optional[int]:
    """解析純整數計數 (例如: "1個", "290戶", "152個" -> 1, 290, 152)"""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)

    clean_str = str(raw).replace(",", "").strip()
    match = re.search(r"(\d+)", clean_str)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_boolean(raw: Any) -> Optional[bool]:
    """解析布林值 (例如: "是", "有" -> True; "否", "無" -> False)"""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw

    s = str(raw).strip()
    if s in ("是", "有", "1", "true", "True"):
        return True
    if s in ("否", "無", "0", "false", "False"):
        return False
    return None


def parse_range_float(raw: Any) -> Tuple[Optional[float], Optional[float]]:
    """解析區間浮點數為 (最小值, 最大值)。

    支援格式:
        "79~90" -> (79.0, 90.0)
        "28~41坪" -> (28.0, 41.0)
        "100~110萬/坪" -> (100.0, 110.0)
        {"price": "100~110", "unit": "萬/坪"} -> (100.0, 110.0)
        {"area": 458.59, "unit": "坪"} -> (458.59, 458.59)
        "45" -> (45.0, 45.0)
        45.0 -> (45.0, 45.0)
    """
    if raw is None:
        return (None, None)

    if isinstance(raw, dict):
        val = raw.get("price") or raw.get("area")
        if val is None:
            return (None, None)
        raw = val

    if isinstance(raw, (int, float)):
        f = float(raw)
        return (f, f)

    s = str(raw).replace(",", "").strip()
    if not s or s in ("-", "--", "待定", "價格待定"):
        return (None, None)

    m_range = re.search(r"(\d+(?:\.\d+)?)\s*(?:~|-)\s*(\d+(?:\.\d+)?)", s)
    if m_range:
        try:
            return (float(m_range.group(1)), float(m_range.group(2)))
        except (ValueError, TypeError):
            pass

    m_single = re.search(r"(\d+(?:\.\d+)?)", s)
    if m_single:
        try:
            f = float(m_single.group(1))
            return (f, f)
        except (ValueError, TypeError):
            pass

    return (None, None)


def parse_room_count(raw: Any) -> Optional[int]:
    """解析房型文字為純整數房數。

    支援格式:
        "一房" -> 1
        "二房" -> 2
        "兩房" -> 2
        "三房" -> 3
        "四房" -> 4
        "五房" -> 5
        "套房" -> 1
        "1房" -> 1
        "3" -> 3
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw

    s = str(raw).strip()
    if not s:
        return None

    chinese_digits = {
        "一": 1,
        "二": 2,
        "兩": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    for ch, n in chinese_digits.items():
        if ch in s:
            return n

    if "套房" in s:
        return 1

    m = re.search(r"(\d+)", s)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            return None
    return None


def parse_households_count(raw: Any) -> Optional[int]:
    """解析戶數字串為總戶數純整數。

    支援格式:
        "1幢，1棟，157戶住家，174戶社會住宅+社區安全設施" -> 331
        "290戶" -> 290
        290 -> 290
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)

    s = str(raw).replace(",", "").strip()
    if not s:
        return None

    matches = re.findall(r"(\d+)\s*戶", s)
    if matches:
        return sum(int(x) for x in matches)

    m = re.search(r"(\d+)", s)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, TypeError):
            return None
    return None

