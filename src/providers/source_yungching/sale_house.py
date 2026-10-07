"""HouseLensAPI - 永慶房屋中古屋領域服務實作 (Yungching Sale House Provider)"""

import logging
from typing import Any, Dict, Optional

from src.core.interfaces.sale_house import ISaleHouseProvider
from src.domain.common import PageResult
from src.domain.enums import Region
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.providers.source_yungching.client import SourceYungchingClient
from src.providers.source_yungching.mappers.sale_house_mapper import (
    map_yungching_sale_detail,
    map_yungching_sale_listing,
)

logger = logging.getLogger(__name__)


class SourceYungchingSaleHouseProvider(ISaleHouseProvider):
    """永慶房屋中古屋領域提供者實作"""

    def __init__(self, client: SourceYungchingClient):
        self._client = client

    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[NormalizedSaleListing]:
        """多元條件中古屋搜尋 (/v2/SearchHouse 端點)"""
        params: Dict[str, Any] = {
            "Page": query.page,
            "Limit": query.page_size,
            "SearchMode": "1",
            "Sequence": "1",
        }

        if query.keywords:
            params["KeyWords"] = query.keywords

        # 縣市與行政區條件 (將標準 region_id 解析為永慶所需之中文縣市名稱)
        county = None
        if query.region_id is not None:
            county = Region.to_chinese_name(query.region_id)
        elif hasattr(query, "region_name") and getattr(query, "region_name"):
            county = str(getattr(query, "region_name"))

        if county:
            params["County"] = county

        if hasattr(query, "section_name") and getattr(query, "section_name"):
            params["District"] = getattr(query, "section_name")

        # 總價範圍篩選 (單位: 萬元)
        if query.min_price_wan is not None:
            params["PriceMin"] = int(query.min_price_wan)
        if query.max_price_wan is not None:
            params["PriceMax"] = int(query.max_price_wan)

        # 屋齡範圍篩選 (單位: 年)
        if query.min_age_years is not None:
            params["AgeMin"] = int(query.min_age_years)
        if query.max_age_years is not None:
            params["AgeMax"] = int(query.max_age_years)

        res = await self._client.get("/v2/SearchHouse", params=params)
        data_block = res.get("Data") or {}
        items_raw = data_block.get("ListObjects") or []
        total_records = data_block.get("Total")
        if total_records is None:
            total_records = len(items_raw)
        else:
            try:
                total_records = int(total_records)
            except (ValueError, TypeError):
                total_records = len(items_raw)

        items = [
            map_yungching_sale_listing(it, query_region=county)
            for it in items_raw
            if isinstance(it, dict)
        ]

        return PageResult.create(
            items=items,
            total_records=total_records,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_sale_house_detail(
        self,
        house_id: str,
        summary: Optional[NormalizedSaleListing] = None,
    ) -> NormalizedSalePropertyDetail:
        """根據房屋唯一 ID (CaseID) 取得完整物件物理詳情與產權五大面積拆解"""
        params = {
            "CaseID": house_id,
            "RefererType": 2,
            "RefererID": 0,
            "IsMultipleLineCaseFeature": "true",
        }
        res = await self._client.get("/v2/houseDetail/Base", params=params)
        data_block = res.get("Data") or {}

        # 直接傳入詳情封包組裝完整物理規格，無須假造 listing
        return map_yungching_sale_detail(raw_detail=data_block, summary=summary)
