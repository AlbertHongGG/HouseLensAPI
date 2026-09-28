"""HouseLensAPI - 頂層資料來源提供者抽象合約 (IHouseSourceProvider)

借鑑 ComicMgr 之極致解耦 Provider 模式，主程式僅依賴此合約，
底層模組自帶社區、中古屋、新建案各領域介面實作。
"""

from abc import ABC, abstractmethod

from src.core.interfaces.community import ICommunityProvider
from src.core.interfaces.new_house import INewHouseProvider
from src.core.interfaces.sale_house import ISaleHouseProvider


class IHouseSourceProvider(ABC):
    """跨平台房產來源頂層服務提供者合約"""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """來源唯一代碼，例如 '591'、'sinyi'、'yungching'"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """來源顯示名稱，例如 '數字科技 591 房屋交易'"""
        pass

    @property
    @abstractmethod
    def community(self) -> ICommunityProvider:
        """社區領域服務接口"""
        pass

    @property
    @abstractmethod
    def sale_house(self) -> ISaleHouseProvider:
        """中古屋領域服務接口"""
        pass

    @property
    @abstractmethod
    def new_house(self) -> INewHouseProvider:
        """新建案領域服務接口"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """來源健康連線檢查"""
        pass
