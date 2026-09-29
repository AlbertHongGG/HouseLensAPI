"""HouseLensAPI - 中古屋領域服務抽象合約 (ISaleHouseProvider)"""

from abc import ABC, abstractmethod

from src.domain.common import PageResult
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)


class ISaleHouseProvider(ABC):
    """中古屋領域服務介面 (所有來源模組之中古屋適配器必須實作)"""

    @abstractmethod
    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[NormalizedSaleListing]:
        """多元條件中古屋搜尋 (回傳標準化刊登規格清單)"""
        pass

    @abstractmethod
    async def get_sale_house_detail(self, house_id: str) -> NormalizedSalePropertyDetail:
        """根據房屋唯一 ID 取得完整物件物理詳情與產權面積純數值規格"""
        pass
