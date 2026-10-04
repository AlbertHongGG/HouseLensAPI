"""HouseLensAPI - 591 中古屋合法性與防腐層校驗器 (Source591SaleHouseValidator)

專職封裝 591 平台中古屋清單項目的合法性判定：
1. 虛擬置頂廣告追蹤碼 (S25xxxxxx / 25xxxxxx)
2. 已收定/成交下架卡片 (delivery == '定交')
3. 顯式廣告標記 (is_ads == '1')
4. 無效或缺失之房屋編號
"""

from typing import Any, Dict, Optional


class Source591SaleHouseValidator:
    """591 中古屋原始資料防腐層校驗器。

    職責：在進入核心領域模型之前，將所有非真實房源（虛擬廣告卡片、已下架卡片、殘缺物件）
    於防腐層徹底攔截，杜絕無效請求與髒資料污染資料庫。
    """

    @staticmethod
    def is_virtual_ad_id(house_id: Optional[str]) -> bool:
        """判定房源編號是否為 591 付費置頂或廣告虛擬曝光追蹤碼。

        591 台灣真實二手房物件 ID 編號格式皆為 S20xxxxxx / S10xxxxxx (或純數字 20xxxxxx / 10xxxxxx)。
        S25xxxxxx (或 25xxxxxx) 為 591 App Gateway 競價置頂虛擬追蹤卡片，後端詳情 API 不存在該實體。
        """
        if not house_id:
            return False
        clean_id = str(house_id).strip().upper()
        if clean_id.startswith("S25"):
            return True
        if clean_id.startswith("25") and len(clean_id) >= 8:
            return True
        return False

    @staticmethod
    def is_deactivated_or_closed(item: Dict[str, Any]) -> bool:
        """判定房源是否已標記為收定、成交或下架。

        591 瀑布流中會夾帶已定交的房源推薦卡片，此類物件後端詳情已下架或無效。
        """
        delivery = str(item.get("delivery") or "").strip()
        if delivery == "定交":
            return True
        return False

    @staticmethod
    def is_explicit_ad(item: Dict[str, Any]) -> bool:
        """判定是否為顯式廣告項目。"""
        if str(item.get("is_ads")) == "1":
            return True
        return False

    @classmethod
    def is_valid_sale_house(cls, item: Optional[Dict[str, Any]]) -> bool:
        """綜合門禁判定：該原始項目是否為 100% 合法且可請求詳情之真實中古屋房源。

        若為廣告、定交卡片或無效 ID，一律回傳 False。
        """
        if not item or not isinstance(item, dict):
            return False

        house_id = item.get("houseid")
        if not house_id:
            return False

        # 1. 檢查是否為顯式廣告
        if cls.is_explicit_ad(item):
            return False

        # 2. 檢查是否為虛擬廣告追蹤碼
        if cls.is_virtual_ad_id(str(house_id)):
            return False

        # 3. 檢查是否為定交或已下架物件
        if cls.is_deactivated_or_closed(item):
            return False

        return True
