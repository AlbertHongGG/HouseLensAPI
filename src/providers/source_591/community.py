"""HouseLensAPI - 591 社區領域服務實作 (591 Community Provider)"""

from typing import Any, Dict

from src.core.interfaces.community import ICommunityProvider
from src.domain.common import PageResult
from src.domain.community import CommunityDetail, CommunitySearchQuery, CommunitySummary
from src.providers.source_591.client import Source591Client
from src.providers.source_591.mappers.community_mapper import (
    map_community_detail,
    map_community_summary,
)


class Source591CommunityProvider(ICommunityProvider):
    """591 社區領域提供者實作"""

    def __init__(self, client: Source591Client):
        self._client = client

    async def search_communities(self, query: CommunitySearchQuery) -> PageResult[CommunitySummary]:
        """多元條件社區檢索 (共用 /v1/search/list 端點)"""
        params: Dict[str, Any] = {
            "page": query.page,
            "page_size": query.page_size,
            "is_sale": query.is_sale,
            "post_type": query.post_type,
            "cm91dGU": "L2NvbW11bml0eS9ob21l",
        }
        if query.region_id is not None:
            params["regionid"] = query.region_id
        if query.section_id is not None:
            params["sectionid"] = query.section_id
        if query.keyword:
            params["keyword"] = query.keyword
        if query.age_ranges:
            params["age"] = ",".join(query.age_ranges)

        res = await self._client.get("market", "/v1/search/list", params=params)
        data_block = res.get("data") or {}
        items_raw = data_block.get("items") or []
        total_records = int(data_block.get("total") or len(items_raw))

        items = [map_community_summary(it) for it in items_raw if isinstance(it, dict)]
        return PageResult.create(
            items=items,
            total_records=total_records,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_community_detail(self, community_id: str) -> CommunityDetail:
        """根據社區 ID 取得完整詳情"""
        params = {
            "id": community_id,
            "cm91dGU": "L2NvbW11bml0eS9kZXRhaWw=",
        }
        res = await self._client.get("market", "/v1/app/gateway/community/info", params=params)
        data_block = res.get("data") or {}
        return map_community_detail(data_block)
