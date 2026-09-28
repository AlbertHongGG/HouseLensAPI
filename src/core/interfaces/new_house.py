"""HouseLensAPI - 新建案領域服務抽象合約 (INewHouseProvider)"""

from abc import ABC, abstractmethod

from src.domain.common import PageResult
from src.domain.new_house import NewHouseDetail, NewHouseSearchQuery, NewHouseSummary


class INewHouseProvider(ABC):
    """新建案領域服務介面 (所有來源模組之新建案適配器必須實作)"""

    @abstractmethod
    async def search_new_houses(self, query: NewHouseSearchQuery) -> PageResult[NewHouseSummary]:
        """多元條件新建案檢索 (支援區域、關鍵字、狀態篩選)"""
        pass

    @abstractmethod
    async def get_new_house_detail(self, new_house_id: str) -> NewHouseDetail:
        """根據建案 ID 取得建案詳情、規劃房型 (layout_v2)、建商團隊與開價資訊"""
        pass
