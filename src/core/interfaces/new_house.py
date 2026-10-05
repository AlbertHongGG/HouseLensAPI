from abc import ABC, abstractmethod
from typing import Optional

from src.domain.common import PageResult
from src.domain.new_house import (
    NewHouseSearchQuery,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)


class INewHouseProvider(ABC):
    """新建案領域服務介面 (所有來源模組之新建案適配器必須實作)"""

    @abstractmethod
    async def search_new_houses(self, query: NewHouseSearchQuery) -> PageResult[NormalizedNewHouseSummary]:
        """多元條件新建案檢索 (支援區域、關鍵字、狀態篩選)"""
        pass

    @abstractmethod
    async def get_new_house_detail(
        self,
        external_project_id: str,
        summary: Optional[NormalizedNewHouseSummary] = None,
    ) -> NormalizedNewHouseDetail:
        """根據外部建案 ID 取得建案詳情、規劃房型、建商團隊與開價資訊"""
        pass
