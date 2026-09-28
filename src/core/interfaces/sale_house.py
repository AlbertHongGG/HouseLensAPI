"""HouseLensAPI - 中古屋領域服務抽象合約 (ISaleHouseProvider)"""

from abc import ABC, abstractmethod

from src.domain.common import PageResult
from src.domain.sale_house import SaleHouseDetail, SaleHouseSearchQuery, SaleHouseSummary


class ISaleHouseProvider(ABC):
    """中古屋領域服務介面 (所有來源模組之中古屋適配器必須實作)"""

    @abstractmethod
    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[SaleHouseSummary]:
        """多元條件中古屋搜尋 (支援縣市、關鍵字、價格區間篩選)"""
        pass

    @abstractmethod
    async def get_sale_house_detail(self, house_id: str) -> SaleHouseDetail:
        """根據房屋唯一 ID 取得完整物件詳情、規格屬性字典、坪數拆解與結構化地理位置"""
        pass
