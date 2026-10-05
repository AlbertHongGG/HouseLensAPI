"""HouseLensAPI - 持久化層 Repository 抽象合約 (Storage Repository Interfaces)

純強型別規範：所有合約僅接受領域正規化規範 (Normalized Specifications)。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set

from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.storage.models.community import CommunityTable
from src.storage.models.new_house import NewHouseTable
from src.storage.models.property import PropertyTable


class ICommunityRepository(ABC):
    """社區持久化倉儲抽象介面"""

    @abstractmethod
    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部社區 ID 中已存在於資料庫者"""
        pass

    @abstractmethod
    async def upsert_from_summary(
        self, summary: NormalizedCommunitySummary, provider_id: str
    ) -> CommunityTable:
        """從 NormalizedCommunitySummary 新增或更新社區節點"""
        pass

    @abstractmethod
    async def upsert_from_detail(
        self, detail: NormalizedCommunityDetail, provider_id: str
    ) -> CommunityTable:
        """從 NormalizedCommunityDetail 新增或更新社區完整規格"""
        pass

    @abstractmethod
    async def get_by_id(self, community_id: str) -> Optional[CommunityTable]:
        """根據內部主鍵 ID 查詢社區"""
        pass

    @abstractmethod
    async def get_by_external_id(
        self, provider_id: str, external_community_id: str
    ) -> Optional[CommunityTable]:
        """根據來源平台代碼與外部社區 ID 查詢社區"""
        pass

    @abstractmethod
    async def search(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityTable]:
        """多條件檢索庫存社區"""
        pass


class IPropertyRepository(ABC):
    """中古屋物件與來源刊登倉儲抽象介面"""

    @abstractmethod
    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部房源刊登 ID 中已存在於資料庫者"""
        pass

    @abstractmethod
    async def upsert_property_with_listing(
        self,
        detail: NormalizedSalePropertyDetail,
        provider_id: str,
        summary: Optional[NormalizedSaleListing] = None,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """寫入物件完整詳情並同步維護來源刊登對應關係 (支援去重合併)"""
        pass

    @abstractmethod
    async def upsert_from_summary(
        self,
        summary: NormalizedSaleListing,
        provider_id: str,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """從清單 Summary 寫入或更新物件與刊登"""
        pass

    @abstractmethod
    async def get_by_id(self, property_id: str) -> Optional[PropertyTable]:
        """根據內部主鍵 ID 查詢客觀物件實體"""
        pass

    @abstractmethod
    async def get_by_listing(
        self, provider_id: str, external_house_id: str
    ) -> Optional[PropertyTable]:
        """根據來源平台刊登 ID 查詢關聯之客觀物件"""
        pass

    @abstractmethod
    async def find_duplicate_candidate(
        self,
        community_name: Optional[str] = None,
        floor_current: Optional[int] = None,
        rooms: Optional[int] = None,
        total_area_pin: Optional[float] = None,
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
        street: Optional[str] = None,
        floor_total: Optional[int] = None,
        area_tolerance_pct: float = 0.02,
        external_community_id: Optional[str] = None,
        is_whole_building: bool = False,
    ) -> Optional[PropertyTable]:
        """依外部社區代碼/社區名（第一級）或行政區路街總樓層（第二級無社區物件）、樓層純整數/整棟標記、房數純整數與坪數誤差尋找庫內可能之重複物件"""
        pass

    @abstractmethod
    async def search(
        self,
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price_wan: Optional[int] = None,
        max_price_wan: Optional[int] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        rooms: Optional[int] = None,
        external_community_id: Optional[str] = None,
        community_uuid: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """多條件檢索庫存中古屋物件"""
        pass


class INewHouseRepository(ABC):
    """新建案持久化倉儲抽象介面"""

    @abstractmethod
    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部新建案 HID 中已存在於資料庫者"""
        pass

    @abstractmethod
    async def upsert_from_detail(
        self, detail: NormalizedNewHouseDetail, provider_id: str
    ) -> NewHouseTable:
        """從 NormalizedNewHouseDetail 新增或更新新建案完整規劃規格"""
        pass

    @abstractmethod
    async def get_by_id(self, new_house_id: str) -> Optional[NewHouseTable]:
        """根據內部主鍵 ID 查詢新建案"""
        pass

    @abstractmethod
    async def get_by_external_id(
        self, provider_id: str, external_project_id: str
    ) -> Optional[NewHouseTable]:
        """根據來源建案外部 ID 查詢新建案"""
        pass

    @abstractmethod
    async def get_by_external_community_id(
        self, provider_id: str, external_community_id: str
    ) -> List[NewHouseTable]:
        """根據外部關聯社區代碼反查其關聯之新建案清單"""
        pass

    @abstractmethod
    async def search(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewHouseTable]:
        """多條件檢索庫存新建案"""
        pass

