"""HouseLensAPI - 永慶房屋相簿防腐資料傳輸物件 (Yungching Photos ACL DTO)

專屬處理永慶房屋圖片動態尺寸替換、封面相片置頂與去重保序。
"""

import re
from typing import Any, Dict, List, Optional


def normalize_yungching_image_url(url: Optional[str], width: int = 1200, height: int = 900) -> Optional[str]:
    """將永慶動態圖片網址正規化為指定解析度大圖 (預設 1200x900)"""
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    # 1. 替換佔位符模板 {0}/{1}
    if "{0}" in cleaned and "{1}" in cleaned:
        return cleaned.replace("{0}", str(width)).replace("{1}", str(height))

    # 2. 替換預設縮圖路由 /ShowPic/240/180/ 或任意尺寸路由 /ShowPic/\d+/\d+/
    cleaned = re.sub(
        r"/ShowPic/\d+/\d+/",
        f"/ShowPic/{width}/{height}/",
        cleaned,
    )
    return cleaned


class SourceYungchingPhotosDTO:
    """永慶房屋相簿防腐資料傳輸物件

    功能職責：
    - 解包完整 response、Data 區塊或直接傳入的圖片字典。
    - 將 Cover 與 Pictures 網址動態升級為 1200x900 超高畫質大圖。
    - 確保封面照片 (Cover) 強制置頂至第一順位 (index 0)。
    - 去除重複 URL 並嚴格維持原始相簿順序。
    """

    def __init__(self, raw: Optional[Any] = None):
        self._cover_raw: Optional[str] = None
        self._pictures_raw: List[str] = []

        if isinstance(raw, dict):
            # 若為完整封包，解包 Data
            data_block = raw.get("Data") if isinstance(raw.get("Data"), dict) else raw
            self._cover_raw = data_block.get("Cover")
            pics = data_block.get("Pictures")
            if isinstance(pics, list):
                self._pictures_raw = [p for p in pics if isinstance(p, str)]
        elif isinstance(raw, list):
            self._pictures_raw = [p for p in raw if isinstance(p, str)]

    @property
    def cover_url(self) -> Optional[str]:
        """傳回高畫質封面照片 URL (1200x900)"""
        if self._cover_raw:
            norm = normalize_yungching_image_url(self._cover_raw)
            if norm:
                return norm
        urls = self.image_urls
        return urls[0] if urls else None

    @property
    def image_urls(self) -> List[str]:
        """傳回標準按序排列的高畫質照片 URL 列表 (封面保證置頂且去重保序)"""
        cover_norm = normalize_yungching_image_url(self._cover_raw) if self._cover_raw else None

        result: List[str] = []
        seen = set()

        # 1. 封面相片置頂至索引 0
        if cover_norm:
            result.append(cover_norm)
            seen.add(cover_norm)

        # 2. 依序加入其餘相片
        for pic in self._pictures_raw:
            norm_pic = normalize_yungching_image_url(pic)
            if norm_pic and norm_pic not in seen:
                result.append(norm_pic)
                seen.add(norm_pic)

        return result
