"""HouseLensAPI - 社區領域服務抽象合約 (ICommunityProvider)"""

from abc import ABC, abstractmethod

from src.domain.common import PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)


class ICommunityProvider(ABC):
    """社區領域服務介面 (所有來源模組之社區適配器必須實作)"""

    @abstractmethod
    async def search_communities(self, query: CommunitySearchQuery) -> PageResult[NormalizedCommunitySummary]:
        """多元條件社區檢索 (支援區域瀏覽、關鍵字、屋齡年份篩選之任意組合)"""
        pass

    @abstractmethod
    async def get_community_detail(self, community_id: str) -> NormalizedCommunityDetail:
        """根據社區唯一 ID 取得完整社區硬體規格、建商營造團隊與公設說明"""
        pass
