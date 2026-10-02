"""HouseLensAPI - 終端文字安全清洗器 (Terminal Text Sanitizer)

負責清洗外部資料中包含的 Emoji、繪文字、控制字符與異常換行，
確保終端機排版穩定且杜絕編碼崩潰 (cp950/GBK 相容)。
"""

import re
from typing import Optional

# 匹配所有 Unicode 高位 Emoji、雜項符號、裝飾符號與修飾符
_EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]"  # 補充平面 Emoji
    r"|[\u2600-\u27bf]"          # 雜項符號與 Dingbats (如星號、箭頭、打勾)
    r"|[\u2300-\u23ff]"          # 雜項技術符號
    r"|[\u2b50-\u2b55]"          # 各式星形與圖示
    r"|[\u200d\ufe0e\ufe0f]"     # 零寬連字與變體選擇器
)

_WHITESPACE_PATTERN = re.compile(r"\s+")


def sanitize_terminal_text(text: Optional[str], max_len: Optional[int] = None) -> str:
    """清洗字串以利終端機安全顯示。

    1. 去除所有 Emoji 與特殊繪文字。
    2. 將換行、Tab 與多重空格壓平成單一空格。
    3. 若指定 max_len 且超過長度，則進行截斷並加上省略號。
    """
    if not text:
        return ""

    # 1. 移除 Emoji 與特殊符號
    cleaned = _EMOJI_PATTERN.sub("", str(text))

    # 2. 壓平空白字元與換行
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    # 3. 長度截斷
    if max_len is not None and max_len > 3 and len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."

    return cleaned
