"""HouseLensAPI - 591 屋齡轉換與區間映射器 (591 Age Mapper)

遵循物件導向與策略適配模式，負責：
1. 將領域層客觀之 (min_age, max_age) 自然數範圍映射為 591 API 官方支援的 age_str Bucket 組合。
2. 將 591 回傳之屋齡文字描述 (如 "1年", "33.5年", "未滿1年") 精確解析為浮點數值。
"""

import re
from typing import List, Optional, Tuple


class Source591AgeMapper:
    """591 平台專屬屋齡適配映射器"""

    # 591 官方標準驗證之屋齡分段定義: (代碼, 區間下限, 區間上限)
    # 經即時封包探勘驗證：10 年以上跨度為 10 年，非 5 年
    BUCKET_DEFINITIONS: List[Tuple[str, float, float]] = [
        ("_5", 0.0, 5.0),
        ("5_10", 5.0, 10.0),
        ("10_20", 10.0, 20.0),
        ("20_30", 20.0, 30.0),
        ("30_40", 30.0, 40.0),
        ("40_", 40.0, float("inf")),
    ]

    @classmethod
    def to_age_str(cls, min_age: Optional[int] = None, max_age: Optional[int] = None) -> Optional[str]:
        """將 (min_age, max_age) 自然數年數映射為 591 專屬 age_str 參數。

        例如:
            (None, 5) -> "_5"
            (None, 10) -> "_5,5_10"
            (5, 10) -> "5_10"
            (10, 30) -> "10_20,20_30"
            (30, None) -> "30_40,40_"
            (40, None) -> "40_"

        若無任何限制或全選，回傳 None（由伺服器回傳全量，避免冗餘參數傳輸）。
        """
        if min_age is None and max_age is None:
            return None

        if min_age is not None and max_age is not None and min_age > max_age:
            raise ValueError(f"min_age ({min_age}) 不能大於 max_age ({max_age})")

        selected_codes: List[str] = []
        for code, b_min, b_max in cls.BUCKET_DEFINITIONS:
            # 若區間下限已大於等於要求的最大屋齡，則不符
            if max_age is not None and b_min >= max_age:
                continue
            # 若區間上限已小於等於要求的最小屋齡，則不符
            if min_age is not None and b_max <= min_age:
                continue
            selected_codes.append(code)

        if not selected_codes:
            return None

        # 若全選 6 個 Bucket，等同於無屋齡過濾，無需浪費 query 參數
        if len(selected_codes) == len(cls.BUCKET_DEFINITIONS):
            return None

        return ",".join(selected_codes)

    @staticmethod
    def parse_building_age(age_str: Optional[str]) -> Optional[float]:
        """將屋齡描述文字解析為乾淨之浮點數數值 (單位: 年)。

        例如:
            "1年" -> 1.0
            "33.5年" -> 33.5
            "全新" / "0年" -> 0.0
            "未滿1年" / "半年" -> 0.5
        """
        if not age_str:
            return None

        clean = age_str.strip()
        if not clean:
            return None

        if clean in ("全新", "0年", "新成屋"):
            return 0.0
        if "未滿1年" in clean or "半年" in clean:
            return 0.5

        # 匹配以「月」或「個月」為單位之極新物件 (例如 "3個月" -> 0.25年)
        if "個月" in clean or "月" in clean:
            match_m = re.search(r"(\d+(?:\.\d+)?)", clean)
            if match_m:
                try:
                    return round(float(match_m.group(1)) / 12.0, 2)
                except (ValueError, TypeError):
                    return 0.1

        # 匹配浮點數或整數 (例如 "33年" -> 33.0, "1.5年" -> 1.5)
        match = re.search(r"(\d+(?:\.\d+)?)", clean)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                return None

        return None
