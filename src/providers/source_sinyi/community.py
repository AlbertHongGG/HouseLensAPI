"""HouseLensAPI - 信義房屋社區領域服務提供者實作 (Sinyi Community Provider)

依循整潔架構與抽象合約 ICommunityProvider，透過信義網頁端網關
提供高品質、強型別、純數值化之社區搜尋與詳情萃取服務。
"""

import logging
import re
from typing import Any, Dict, Optional

from src.core.exceptions import ProviderResponseError
from src.core.interfaces.community import ICommunityProvider
from src.domain.common import PageResult
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.mappers import (
    map_sinyi_community_detail,
    map_sinyi_community_list_item,
)
from src.providers.source_sinyi.query_builders import SinyiCommunityQueryBuilder

logger = logging.getLogger(__name__)


class SourceSinyiCommunityProvider(ICommunityProvider):
    """信義房屋社區領域服務提供者實作"""

    def __init__(self, client: SourceSinyiClient):
        self._client = client

    async def search_communities(
        self, query: CommunitySearchQuery
    ) -> PageResult[NormalizedCommunitySummary]:
        """多元條件社區檢索 (調用 /searchCommunity.php 網頁端端點)"""
        payload = SinyiCommunityQueryBuilder.build_search_payload(query)
        res = await self._client.post_web_api("/searchCommunity.php", payload)

        content = res.get("content") or {}
        items_raw = content.get("object") or []
        total_records = content.get("totalCnt")
        if total_records is None:
            total_records = len(items_raw)
        else:
            try:
                total_records = int(total_records)
            except (ValueError, TypeError):
                total_records = len(items_raw)

        items = [map_sinyi_community_list_item(it) for it in items_raw if isinstance(it, dict)]

        # 外部代碼直接檢索防護 (Direct ID Fallback):
        # 若清單搜尋無結果，且 query.keywords 符合信義社區英數代碼規格 (如 G0000316, 0032408)，嘗試直查詳情端點
        if not items and query.keywords and query.keywords.strip():
            kw = query.keywords.strip()
            if re.match(r"^[A-Za-z0-9]{6,10}$", kw):
                try:

                    fallback_detail = await self.get_community_detail(kw)
                    fallback_summary = NormalizedCommunitySummary(
                        provider_id="sinyi",
                        external_community_id=fallback_detail.external_community_id,
                        community_name=fallback_detail.community_name,
                        region_name=fallback_detail.region_name or "",
                        section_name=fallback_detail.section_name or "",
                        address=fallback_detail.address or "",
                        coordinates=fallback_detail.coordinates,
                        avg_unit_price_wan=fallback_detail.avg_unit_price_wan,
                        building_age_years=fallback_detail.building_age_years,
                        cover_image_url=fallback_detail.cover_image_url,
                        url=fallback_detail.url,
                    )
                    items = [fallback_summary]
                    total_records = 1
                except Exception as e:
                    logger.debug("以代碼 %s 直查詳情兜底未命中: %s", kw, e)

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
        """根據社區外部唯一代碼取得完整社區規格 (調用 /getCommunityContent.php 網頁端端點)"""
        clean_id = str(external_community_id).strip()
        payload = {"commId": clean_id}
        res = await self._client.post_web_api("/getCommunityContent.php", payload)

        content = res.get("content")
        if not content or not isinstance(content, dict):
            raise ProviderResponseError("sinyi", f"信義房屋社區詳情未回傳有效內容 (commId: {clean_id})")

        return map_sinyi_community_detail(raw_detail=res, summary=summary)
