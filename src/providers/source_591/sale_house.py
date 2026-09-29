"""HouseLensAPI - 591 中古屋領域服務實作 (591 Sale House Provider)"""

from typing import Any, Dict

from src.core.interfaces.sale_house import ISaleHouseProvider
from src.domain.common import PageResult
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.providers.source_591.client import Source591Client
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.mappers.sale_house_mapper import (
    map_sale_house_detail,
    map_sale_house_summary,
)


class Source591SaleHouseProvider(ISaleHouseProvider):
    """591 中古屋領域服務提供者實作 (內部全自理參數映射與資料正規化)"""

    def __init__(self, client: Source591Client):
        self._client = client

    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[NormalizedSaleListing]:
        """多元條件中古屋搜尋 (自動過濾廣告並轉換為標準 NormalizedSaleListing)"""
        params: Dict[str, Any] = {
            "p": query.page,
            "version": "8.13.0.975",
            "newlist": "1",
            "kind": getattr(query, "kind", 0) or 0,
            "o": query.sort_order or "90",

            "cm91dGU": "L2hvdXNlL2xpc3Q=",
        }

        # 591 專屬查詢參數映射
        if query.region_id is not None:
            params["regionid"] = query.region_id
        if query.section_id is not None:
            params["sectionid"] = query.section_id
        if query.keywords:
            params["keywords"] = query.keywords
        if query.min_price_wan is not None:
            params["min_price"] = query.min_price_wan
        if query.max_price_wan is not None:
            params["max_price"] = query.max_price_wan
        if query.rooms is not None:
            params["room"] = query.rooms

        # 屋齡區間轉換由模組內部 Mapper 自理
        if query.min_age_years is not None or query.max_age_years is not None:
            min_a = int(query.min_age_years) if query.min_age_years is not None else None
            max_a = int(query.max_age_years) if query.max_age_years is not None else None
            age_str = Source591AgeMapper.to_age_str(min_age=min_a, max_age=max_a)
            if age_str:
                params["age_str"] = age_str

        res = await self._client.get("house", "/v1/app/gateway/sale/list", params=params)
        data_block = res.get("data") or {}
        items_raw = data_block.get("items") or []

        raw_records = data_block.get("records")
        total_records = int(raw_records) if raw_records else len(items_raw)

        # 透過模組內部 mapper 清洗為純淨標準規格 (過濾廣告 is_ads == "1")
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

    async def get_sale_house_detail(self, house_id: str) -> NormalizedSalePropertyDetail:
        """根據房屋唯一代號取得清洗完畢之 NormalizedSalePropertyDetail"""
        clean_id = house_id.lstrip("S") if house_id.startswith("S") else house_id
        params = {
            "id": clean_id,
            "cm91dGU": "L3NhbGVob3VzZS9kZXRhaWw=",
        }

        res = await self._client.get("house", "/v1/app/gateway/sale/detail", params=params)
        data_block = res.get("data") or {}
        return map_sale_house_detail(data_block)
