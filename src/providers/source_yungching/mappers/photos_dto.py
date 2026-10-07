"""HouseLensAPI - 永慶房屋相簿防腐資料傳輸物件 (Yungching Photos ACL DTO)

專屬處理永慶房屋圖片動態尺寸替換、封面相片置頂與去重保序。
支援社區 (Pic.yungching.com.tw 模板路由) 與中古屋 (yccdn.yungching.com.tw CDN 參數路由)。
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

    # 1. 替換佔位符模板 {0}/{1} (如社區圖片)
    if "{0}" in cleaned and "{1}" in cleaned:
        return cleaned.replace("{0}", str(width)).replace("{1}", str(height))

    # 2. 替換預設縮圖路由 /ShowPic/240/180/ 或任意尺寸路由 /ShowPic/\d+/\d+/
    if "/ShowPic/" in cleaned:
        cleaned = re.sub(
            r"/ShowPic/\d+/\d+/",
            f"/ShowPic/{width}/{height}/",
            cleaned,
        )
        return cleaned

    # 3. 替換 CDN 圖片動態 Query 參數 (如中古屋圖片 yccdn.yungching.com.tw)
    if "width=" in cleaned and "height=" in cleaned:
        cleaned = re.sub(
            r"width=\d+&height=\d+",
            f"width={width}&height={height}",
            cleaned,
        )
        return cleaned

    return cleaned


class SourceYungchingPhotosDTO:
    """永慶房屋社區相簿防腐資料傳輸物件"""

    def __init__(self, raw: Optional[Any] = None):
        self._cover_raw: Optional[str] = None
        self._pictures_raw: List[str] = []

        if isinstance(raw, dict):
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

        if cover_norm:
            result.append(cover_norm)
            seen.add(cover_norm)

        for pic in self._pictures_raw:
            norm_pic = normalize_yungching_image_url(pic)
            if norm_pic and norm_pic not in seen:
                result.append(norm_pic)
                seen.add(norm_pic)

        return result


class SourceYungchingSalePhotosDTO:
    """永慶房屋中古屋相簿防腐資料傳輸物件

    專屬處理 /v2/houseDetail/Base 回應中之 Pictures 陣列：
    - 支援字典項目 (含 'Url', 'ClearUrl') 或純字串項目。
    - 將網址動態升級為 width=1200&height=900 高畫質圖。
    - 首張照片強制置頂至第一順位 (index 0) 作為封面。
    - 自動去除重複 URL 並保證原有順序。
    """

    def __init__(self, raw: Optional[Any] = None):
        self._pictures_raw: List[str] = []
        self._cover_raw: Optional[str] = None

        if isinstance(raw, dict):
            data_block = raw.get("Data") if isinstance(raw.get("Data"), dict) else raw
            self._cover_raw = data_block.get("Picture") or data_block.get("Cover")
            pics = data_block.get("Pictures") or data_block.get("PictureList")
            if isinstance(pics, list):
                for p in pics:
                    if isinstance(p, dict):
                        u = p.get("Url") or p.get("ClearUrl")
                        if u and isinstance(u, str):
                            self._pictures_raw.append(u)
                    elif isinstance(p, str):
                        self._pictures_raw.append(p)

            floor_plan = data_block.get("FloorPlan") or data_block.get("SpcUrl")
            if isinstance(floor_plan, str) and floor_plan and "non-layout" not in floor_plan:
                self._pictures_raw.append(floor_plan)
        elif isinstance(raw, list):
            for p in raw:
                if isinstance(p, dict):
                    u = p.get("Url") or p.get("ClearUrl")
                    if u and isinstance(u, str):
                        self._pictures_raw.append(u)
                elif isinstance(p, str):
                    self._pictures_raw.append(p)

    @property
    def cover_url(self) -> Optional[str]:
        """傳回首張高畫質照片 URL (1200x900)"""
        urls = self.image_urls
        if urls:
            return urls[0]
        if self._cover_raw:
            return normalize_yungching_image_url(self._cover_raw)
        return None

    @property
    def image_urls(self) -> List[str]:
        """傳回按序排列的高畫質照片 URL 列表 (去重保序，首圖保證置頂)"""
        result: List[str] = []
        seen = set()

        # 若外部有明確提供 cover 且不在列表中，優先置頂
        if self._cover_raw:
            c_norm = normalize_yungching_image_url(self._cover_raw)
            if c_norm and c_norm not in seen:
                result.append(c_norm)
                seen.add(c_norm)

        for p in self._pictures_raw:
            norm_pic = normalize_yungching_image_url(p)
            if norm_pic and norm_pic not in seen:
                result.append(norm_pic)
                seen.add(norm_pic)

        return result
