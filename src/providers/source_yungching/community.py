"""HouseLensAPI - 永慶房屋社區領域服務實作 (Yungching Community Provider)"""

import logging
from typing import Any, Dict, Optional

from src.core.interfaces.community import ICommunityProvider
from src.domain.common import GeoPoint, PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.enums import Region
from src.providers.source_yungching.client import SourceYungchingClient
from src.providers.source_yungching.mappers.community_mapper import (
    map_yungching_community_detail,
    map_yungching_community_summary,
)
from src.providers.source_yungching.mappers.photos_dto import normalize_yungching_image_url

logger = logging.getLogger(__name__)


class SourceYungchingCommunityProvider(ICommunityProvider):
    """永慶房屋社區領域提供者實作"""

    def __init__(self, client: SourceYungchingClient):
        self._client = client

    async def search_communities(self, query: CommunitySearchQuery) -> PageResult[NormalizedCommunitySummary]:
        """多元條件社區檢索 (/v1/SearchCommunityList 端點)"""
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

        # 屋齡範圍轉換 (永慶格式: "~10" 或 "10~20")
        if query.min_age_years is not None or query.max_age_years is not None:
            min_a = int(query.min_age_years) if query.min_age_years is not None else ""
            max_a = int(query.max_age_years) if query.max_age_years is not None else ""
            params["MutiBuildAge"] = f"{min_a}~{max_a}"

        res = await self._client.get("/v1/SearchCommunityList", params=params)
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

        items = [map_yungching_community_summary(it) for it in items_raw if isinstance(it, dict)]
        return PageResult.create(
            items=items,
            total_records=total_records,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_community_detail(
        self,
        external_community_id: str,
        summary: Optional[NormalizedCommunitySummary] = None,
    ) -> NormalizedCommunityDetail:
        """根據社區外部 ID 取得完整正規化詳情 (最小必要資訊取自 summary，主檔直取 detail)"""
        params = {"CommunityID": external_community_id}
        res = await self._client.get("/v1/SearchCommunityDetail", params=params)
        data_block = res.get("Data") or {}

        # 若未提供 summary (例如單純依 ID 直接查詢)，從 detail 的基礎同名欄位建立保底最小必要 summary
        if summary is None:
            lat_raw = data_block.get("Lat")
            lng_raw = data_block.get("Lng")
            coords: Optional[GeoPoint] = None
            if lat_raw is not None and lng_raw is not None:
                try:
                    coords = GeoPoint(lat=float(lat_raw), lng=float(lng_raw))
                except (ValueError, TypeError):
                    coords = None

            trade_info = data_block.get("TradeInfo") or {}
            avg_price_raw = trade_info.get("AvgUnitPrice") if isinstance(trade_info, dict) else None
            avg_price: Optional[float] = None
            if avg_price_raw is not None:
                try:
                    avg_price = float(avg_price_raw)
                except (ValueError, TypeError):
                    avg_price = None

            cover_norm = normalize_yungching_image_url(data_block.get("Cover"))

            summary = NormalizedCommunitySummary(
                provider_id="yungching",
                external_community_id=str(data_block.get("ID") or external_community_id),
                community_name=str(data_block.get("Name") or "").strip(),
                region_name="",
                section_name="",
                address=str(data_block.get("Address") or "").strip(),
                coordinates=coords,
                avg_unit_price_wan=avg_price,
                cover_image_url=cover_norm,
                building_type=None,
                purpose=None,
                housing_status=None,
                shopping_district=None,
                transport=None,
            )

        return map_yungching_community_detail(summary=summary, raw_detail=data_block)
