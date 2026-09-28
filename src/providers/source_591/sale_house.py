"""HouseLensAPI - 591 中古屋領域服務實作 (591 Sale House Provider)"""

from typing import Any, Dict

from src.core.interfaces.sale_house import ISaleHouseProvider
from src.domain.common import PageResult
from src.domain.sale_house import SaleHouseDetail, SaleHouseSearchQuery, SaleHouseSummary
from src.providers.source_591.client import Source591Client
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.mappers.sale_house_mapper import (
    map_sale_house_detail,
    map_sale_house_summary,
)


class Source591SaleHouseProvider(ISaleHouseProvider):
    """591 中古屋領域提供者實作"""

    def __init__(self, client: Source591Client):
        self._client = client

    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[SaleHouseSummary]:
        """多元條件中古屋搜尋 (自動過濾廣告建案)"""
        params: Dict[str, Any] = {
            "p": query.page,
            "version": "8.13.0.975",  # 必要參數：控制回傳 JSON 結構格式
            "newlist": "1",           # 開啟每頁筆數最佳化
            "kind": query.kind if query.kind is not None else 0,
            "o": query.sort_order or "90",
            "cm91dGU": "L2hvdXNlL2xpc3Q=",
        }
        if query.region_id is not None:
            params["regionid"] = query.region_id
        if query.section_id is not None:
            params["sectionid"] = query.section_id
        if query.keywords:
            params["keywords"] = query.keywords
        if query.min_price is not None:
            params["min_price"] = query.min_price
        if query.max_price is not None:
            params["max_price"] = query.max_price
        if query.min_age is not None or query.max_age is not None:
            age_str = Source591AgeMapper.to_age_str(min_age=query.min_age, max_age=query.max_age)
            if age_str:
                params["age_str"] = age_str

        res = await self._client.get("house", "/v1/app/gateway/sale/list", params=params)
        data_block = res.get("data") or {}
        items_raw = data_block.get("items") or []

        raw_records = data_block.get("records")
        total_records = int(raw_records) if raw_records else len(items_raw)

        # 透過 mapper 進行過濾 (is_ads == "1" 會回傳 None)
        valid_items = []
        for it in items_raw:
            if isinstance(it, dict):
                mapped = map_sale_house_summary(it)
                if mapped is not None:
                    valid_items.append(mapped)

        return PageResult.create(
            items=valid_items,
            total_records=total_records,
            page=query.page,
            page_size=len(items_raw) if items_raw else 20,
        )

    async def get_sale_house_detail(self, house_id: str) -> SaleHouseDetail:
        """根據房屋唯一代號 (支援 S 開頭或純數字) 取得完整詳情"""
        clean_id = house_id.lstrip("S") if house_id.startswith("S") else house_id
        params = {
            "id": clean_id,
            "cm91dGU": "L3NhbGVob3VzZS9kZXRhaWw=",
        }

        res = await self._client.get("house", "/v1/app/gateway/sale/detail", params=params)
        data_block = res.get("data") or {}
        return map_sale_house_detail(data_block)
