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


def parse_floor(raw: Any) -> Tuple[Optional[int], Optional[int], bool]:
    """解析樓層為 (所在樓層純整數, 總樓層純整數, 是否為整棟銷售)。

    支援格式:
        "2F/24F" -> (2, 24, False)
        "2樓/共24樓" -> (2, 24, False)
        "B1/12F" -> (-1, 12, False)
        "整棟/5F" -> (None, 5, True)
        "全棟/5F" -> (None, 5, True)
        "99" / 99 -> (None, None, True) (591 協議中代表整棟透天/別墅)
        "整棟" / "全棟" -> (None, None, True)
        2 -> (2, None, False)
    """
    if raw is None:
        return (None, None, False)

    if raw == 99 or str(raw).strip() == "99":
        return (None, None, True)

    if isinstance(raw, int):
        return (raw, None, False)

    clean_str = str(raw).strip()
    if not clean_str:
        return (None, None, False)

    is_whole_building = False
    curr_floor: Optional[int] = None
    total_floor: Optional[int] = None

    if "/" in clean_str:
        parts = clean_str.split("/", 1)
        curr_part = parts[0].strip()
        total_part = parts[1].strip()

        if curr_part in ("整棟", "全棟", "99"):
            is_whole_building = True
            curr_floor = None
        else:
            curr_floor = _parse_single_floor(curr_part)

        total_floor = _parse_single_floor(total_part)
    else:
        if clean_str in ("整棟", "全棟", "99"):
            is_whole_building = True
            curr_floor = None
        else:
            curr_floor = _parse_single_floor(clean_str)

    return (curr_floor, total_floor, is_whole_building)


def _parse_single_floor(s: str) -> Optional[int]:
    """輔助解析單一樓層字串 (支援地下室 B1 -> -1，嚴格過濾 99 與整棟文字)"""
    if not s:
        return None
    s = s.upper().replace("F", "").replace("樓", "").replace("共", "").strip()
    if s in ("整棟", "全棟", "99", "頂樓"):
        return None
    if s.startswith("B"):
        b_num = s.replace("B", "").strip()
        if b_num.isdigit():
            return -int(b_num)
    if s.isdigit():
        val = int(s)
        return None if val == 99 else val
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


def clean_optional_str(raw: Any) -> Optional[str]:
    """清洗可選文字欄位，將空字串、空白與常見無效佔位符統一純化為 None。

    支援過濾: "", "   ", "-", "--", "---", "無", "暫無", "未提供", "待定", "None", "null"
    """
    if raw is None:
        return None

    s = str(raw).strip()
    if not s:
        return None

    invalid_placeholders = {
        "-",
        "--",
        "---",
        "無",
        "暫無",
        "暫無資料",
        "暫無數據",
        "暂无",
        "暂无数据",
        "未提供",
        "待定",
        "價格待定",
        "不詳",
        "未知",
        "None",
        "none",
        "null",
        "NULL",
    }
    if s in invalid_placeholders:
        return None

    return s


def clean_park_price(raw: Any) -> Optional[str]:
    """清洗並規範化車位價格描述。

    處理 591 實價登錄統計缺陷 (未排除無車位交易導致的 0~X萬):
        - "0~320萬" / "0～320萬" / "0－320萬" -> "最高 320萬"
        - "0~2,750萬" / "0～2,750" -> "最高 2,750萬"
        - "290~330萬" / "290～330萬" -> "290~330萬" (保持客觀區間)
        - "350萬" -> "350萬" (單一價格)
        - "" / None / "-" -> None
    """
    if raw is None:
        return None

    unit = "萬"
    price_str = ""

    if isinstance(raw, dict):
        p_val = raw.get("price")
        unit = raw.get("unit") or "萬"
        price_str = str(p_val or "").strip()
    else:
        price_str = str(raw).strip()

    cleaned = clean_optional_str(price_str)
    if not cleaned:
        return None

    # 去除可能已自帶的單位進行正規化分析
    base_str = cleaned.replace("萬元", "").replace("萬", "").strip()

    # 1. 偵測 0~X 模式 (591 統計 Bug 修復，支援全形與半形符號: ~ ～ - －)
    m_zero_to_max = re.match(r"^0\s*[~～\-－]\s*(\d[\d,]*(?:\.\d+)?)$", base_str)
    if m_zero_to_max:
        max_p = m_zero_to_max.group(1)
        return f"最高 {max_p}{unit}"

    # 2. 偵測正常區間 X~Y (支援全形與半形符號)
    m_range = re.match(
        r"^(\d[\d,]*(?:\.\d+)?)\s*[~～\-－]\s*(\d[\d,]*(?:\.\d+)?)$", base_str
    )
    if m_range:
        min_p = m_range.group(1)
        max_p = m_range.group(2)
        return f"{min_p}~{max_p}{unit}"

    # 3. 偵測單一純數字
    m_single = re.match(r"^(\d[\d,]*(?:\.\d+)?)$", base_str)
    if m_single:
        return f"{m_single.group(1)}{unit}"

    # 其他自訂文字描述，若非空則保留
    return cleaned



def clean_parking_count(
    count_raw: Any,
    park_raw: Any = None,
    rate_raw: Any = None,
) -> Optional[int]:
    """清洗社區車位總數純整數。

    語意辨析:
        - 591 封包中 all_park_num=0 且 park="" 且 park_rate="" 時，代表平台無硬體數據 (未登錄)，回傳 None。
        - 若 park 描述中明確含有 "無車位"，才判定為客觀 0。
        - 正整數正常解析為純整數。
    """
    count = parse_int_count(count_raw)
    if count is None:
        return None

    if count > 0:
        return count

    # count == 0 時，研判是否為假性 0 (缺失值)
    p_desc = clean_optional_str(park_raw)
    r_desc = clean_optional_str(rate_raw)

    if p_desc is None and r_desc is None:
        # 完全無任何附帶規格，代表平台未登錄，而非物理上零車位
        return None

    if p_desc and ("無車位" in p_desc or "零車位" in p_desc):
        return 0

    return None


def parse_parking_planning(desc: Any) -> Tuple[Optional[int], Optional[int]]:
    """解析車位規劃型態與數量，回傳 (平面車位數, 機械車位數)。

    支援範例:
        "平面式111個、機械式41個" -> (111, 41)
        "平面式192個" -> (192, None)
        "機械式50個" -> (None, 50)
        "平面 1 個、機械 33 個" -> (1, 33)
        "暫無" -> (None, None)
    """
    if desc is None:
        return (None, None)
    s = str(desc).strip()
    if not s or s in ("暫無", "無", "暫無資料"):
        return (None, None)

    plane_cnt: Optional[int] = None
    mech_cnt: Optional[int] = None

    m_plane = re.search(r"平面(?:式)?\s*(\d+)\s*個", s)
    if m_plane:
        try:
            plane_cnt = int(m_plane.group(1))
        except (ValueError, TypeError):
            pass

    m_mech = re.search(r"機械(?:式)?\s*(\d+)\s*個", s)
    if m_mech:
        try:
            mech_cnt = int(m_mech.group(1))
        except (ValueError, TypeError):
            pass

    return (plane_cnt, mech_cnt)


def parse_parking_ratio(ratio: Any) -> Tuple[Optional[str], Optional[float]]:
    """解析車位配比，回傳 (標準字串, 純數值比率)。

    支援範例:
        "1:0.46" -> ("1:0.46", 0.46)
        "1:1" -> ("1:1", 1.0)
        "1:1.05" -> ("1:1.05", 1.05)
    """
    if ratio is None:
        return (None, None)
    s = str(ratio).strip()
    if not s or s in ("暫無", "無", "暫無資料"):
        return (None, None)

    m = re.search(r"1\s*:\s*(\d+(?:\.\d+)?)", s)
    if m:
        try:
            val = float(m.group(1))
            return (s, val)
        except (ValueError, TypeError):
            return (s, None)

    return (s, None)


def parse_charging_piles(desc: Any) -> Tuple[Optional[str], Optional[bool]]:
    """解析充電設備規劃，回傳 (標準描述, 是否具備充電設備或預留布林值)。

    支援範例:
        "有充電設備（含預留）" -> ("有充電設備（含預留）", True)
        "無充電設備" -> ("無充電設備", False)
        "" -> (None, None)
    """
    if desc is None:
        return (None, None)
    s = str(desc).strip()
    if not s or s in ("暫無", "無", "暫無資料"):
        return (None, None)

    if "有充電" in s or "預留" in s:
        return (s, True)
    if "無充電" in s:
        return (s, False)

    return (s, None)


def parse_coordinate(val: Any) -> Optional[float]:
    """解析經緯度坐標浮點數。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if f != 0.0 else None

    s = str(val).strip()
    if not s or s in ("暫無", "無", "0"):
        return None

    try:
        f = float(s)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


def parse_new_house_parking_price(
    raw: Any,
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """解析新建案車位開價，回傳 (描述字串, 最低價萬元, 最高價萬元)。

    支援 591 封包結構:
        {'pending': 0, 'price': '155~320', 'unit': '萬'} -> ("155~320萬", 155.0, 320.0)
        {'pending': 0, 'price': '380', 'unit': '萬'} -> ("380萬", 380.0, 380.0)
        {'pending': 1, 'price': '價格待定', 'unit': ''} -> ("價格待定", None, None)
    """
    if raw is None:
        return (None, None, None)

    pending = 0
    price_val = ""
    unit = "萬"

    if isinstance(raw, dict):
        pending = int(raw.get("pending") or 0)
        price_val = str(raw.get("price") or "").strip()
        unit = str(raw.get("unit") or "萬").strip()
    else:
        price_val = str(raw).strip()

    if not price_val or price_val in ("暫無", "無", "暫無資料"):
        return (None, None, None)

    if pending == 1 or "待定" in price_val:
        return ("價格待定", None, None)

    min_p, max_p = parse_range_float(price_val)
    desc = f"{price_val}{unit}" if unit and not price_val.endswith(unit) else price_val
    return (desc, min_p, max_p)



