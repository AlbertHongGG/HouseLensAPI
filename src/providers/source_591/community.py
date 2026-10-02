"""HouseLensAPI - 591 社區領域服務實作 (591 Community Provider)"""

from typing import Any, Dict

from src.core.interfaces.community import ICommunityProvider
from src.domain.common import PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_591.client import Source591Client
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.mappers.community_mapper import (
    map_community_detail,
    map_community_summary,
)


class Source591CommunityProvider(ICommunityProvider):
    """591 社區領域提供者實作 (內部全自理參數映射與資料正規化)"""

    def __init__(self, client: Source591Client):
        self._client = client

    async def search_communities(self, query: CommunitySearchQuery) -> PageResult[NormalizedCommunitySummary]:
        """多元條件社區檢索 (共用 /v1/search/list 端點)"""
        params: Dict[str, Any] = {
            "page": query.page,
            "page_size": query.page_size,
            "is_sale": 0,
            "post_type": "8,2",
            "cm91dGU": "L2NvbW11bml0eS9ob21l",
        }
        if query.region_id is not None:
            params["regionid"] = query.region_id
        if query.section_id is not None:
            params["sectionid"] = query.section_id
        if query.keywords:
            params["keyword"] = query.keywords

        # 591 專屬屋齡查詢代碼轉換由模組自理
        if query.min_age_years is not None or query.max_age_years is not None:
            min_a = int(query.min_age_years) if query.min_age_years is not None else None
            max_a = int(query.max_age_years) if query.max_age_years is not None else None
            age_str = Source591AgeMapper.to_age_str(min_age=min_a, max_age=max_a)
            if age_str:
                params["age"] = age_str

        res = await self._client.get("market", "/v1/search/list", params=params)
        data_block = res.get("data") or {}
        items_raw = data_block.get("items") or []
        paginate = data_block.get("paginate") or {}
        raw_total = paginate.get("total") or data_block.get("total")
        total_records = int(raw_total) if raw_total is not None else len(items_raw)

        items = [map_community_summary(it) for it in items_raw if isinstance(it, dict)]
        return PageResult.create(
            items=items,
            total_records=total_records,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_community_detail(self, community_id: str) -> NormalizedCommunityDetail:
        """根據社區 ID 取得完整正規化詳情"""
        params = {
            "id": community_id,
            "cm91dGU": "L2NvbW11bml0eS9kZXRhaWw=",
        }
        res = await self._client.get("market", "/v1/app/gateway/community/info", params=params)
        data_block = res.get("data") or {}
        return map_community_detail(data_block)
