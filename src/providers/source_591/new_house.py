from typing import Any, Dict, Optional

from src.core.interfaces.new_house import INewHouseProvider
from src.domain.common import PageResult
from src.domain.new_house import (
    NewHouseSearchQuery,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.providers.source_591.client import Source591Client
from src.providers.source_591.mappers.new_house_mapper import (
    map_new_house_detail,
    map_new_house_summary,
)


class Source591NewHouseProvider(INewHouseProvider):
    """591 新建案領域提供者實作 (Anti-Corruption Layer)"""

    def __init__(self, client: Source591Client):
        self._client = client

    async def search_new_houses(self, query: NewHouseSearchQuery) -> PageResult[NormalizedNewHouseSummary]:
        """多元條件新建案搜尋"""
        params: Dict[str, Any] = {
            "searchtype": 1,
            "p": query.page,
            "limit": query.page_size,
            "cm91dGU": "L25ld2hvdXNlL2hvdXNpbmdsaXN0",
        }
        if query.region_id is not None:
            params["regionid"] = query.region_id
        if query.keywords:
            params["keywords"] = query.keywords

        # 591 狀態對照 (1: 預售屋, 2: 新成屋)
        statuses = []
        if query.is_presale:
            statuses.append("1")
        if query.is_new_construction:
            statuses.append("2")
        if statuses:
            params["buildstatus"] = ",".join(statuses)

        res = await self._client.get("newhouse", "/v1/list-search", params=params)
        data_block = res.get("data") or {}
        items_raw = data_block.get("items") or []
        total_records = int(data_block.get("total") or len(items_raw))

        items = [
            map_new_house_summary(it)
            for it in items_raw
            if isinstance(it, dict) and "hid" in it and it.get("hid") is not None
        ]
        return PageResult.create(
            items=items,
            total_records=total_records,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_new_house_detail(
        self,
        external_project_id: str,
        summary: Optional[NormalizedNewHouseSummary] = None,
    ) -> NormalizedNewHouseDetail:
        """根據建案外部 ID 取得完整新建案詳情"""
        params = {
            "id": external_project_id,
            "short_video": 1,
            "cm91dGU": "L25ld2hvdXNlL2hvdXNpbmdkZXRhaWw=",
        }
        res = await self._client.get("newhouse", "/v1/detail/base-info", params=params)
        data_block = res.get("data") or {}
        return map_new_house_detail(data=data_block, summary=summary)
