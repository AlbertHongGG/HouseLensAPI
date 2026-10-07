"""HouseLensAPI - 永慶房屋相簿防腐資料傳輸物件 (Yungching Photos ACL DTO)

採用物件導向樣板方法模式 (Template Method Pattern)：
- BaseYungchingPhotosDTO 封裝統一之尺寸升級、去重保序與封面強制置頂 (Index 0)。
- 領域子類別 (Community, Sale) 僅專注於解析各領域特有封包階層結構。
"""

from abc import ABC, abstractmethod
import re
from typing import Any, List, Optional


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


class BaseYungchingPhotosDTO(ABC):
    """永慶房屋相簿防腐抽象基底類別 (Template Method Pattern)"""

    def __init__(self, raw: Optional[Any] = None):
        self._cover_raw: Optional[str] = None
        self._pictures_raw: List[str] = []
        if raw is not None:
            self._extract_payload(raw)

    @abstractmethod
    def _extract_payload(self, raw: Any) -> None:
        """由具體領域子類別解析專屬原始封包結構，填充 _cover_raw 與 _pictures_raw"""
        pass

    @property
    def cover_url(self) -> Optional[str]:
        """傳回高畫質封面照片 URL (1200x900)"""
        urls = self.image_urls
        if urls:
            return urls[0]
        if self._cover_raw:
            return normalize_yungching_image_url(self._cover_raw)
        return None

    @property
    def image_urls(self) -> List[str]:
        """傳回標準按序排列的高畫質照片 URL 列表 (封面保證置頂且去重保序)"""
        result: List[str] = []
        seen = set()

        # 若外部有明確提供封面相片，強制置頂至第一順位
        if self._cover_raw:
            c_norm = normalize_yungching_image_url(self._cover_raw)
            if c_norm and c_norm not in seen:
                result.append(c_norm)
                seen.add(c_norm)

        for pic in self._pictures_raw:
            norm_pic = normalize_yungching_image_url(pic)
            if norm_pic and norm_pic not in seen:
                result.append(norm_pic)
                seen.add(norm_pic)

        return result


class SourceYungchingCommunityPhotosDTO(BaseYungchingPhotosDTO):
    """永慶房屋社區相簿防腐資料傳輸物件"""

    def _extract_payload(self, raw: Any) -> None:
        if isinstance(raw, dict):
            data_block = raw.get("Data") if isinstance(raw.get("Data"), dict) else raw
            self._cover_raw = data_block.get("Cover")
            pics = data_block.get("Pictures")
            if isinstance(pics, list):
                self._pictures_raw = [p for p in pics if isinstance(p, str)]
        elif isinstance(raw, list):
            self._pictures_raw = [p for p in raw if isinstance(p, str)]


# 社區相簿別名
SourceYungchingPhotosDTO = SourceYungchingCommunityPhotosDTO


class SourceYungchingSalePhotosDTO(BaseYungchingPhotosDTO):
    """永慶房屋中古屋相簿防腐資料傳輸物件

    專屬處理 /v2/houseDetail/Base 回應中之相片清單與格局圖：
    - 支援字典項目 (含 'Url', 'ClearUrl') 或純字串項目。
    - 支援 Picture / Cover / PictureList / Pictures / FloorPlan / SpcUrl。
    """

    def _extract_payload(self, raw: Any) -> None:
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
