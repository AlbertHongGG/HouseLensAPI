"""HouseLensAPI - 信義房屋中古屋領域服務適配器 (Sinyi Sale House Provider)

實作標準 ISaleHouseProvider 介面，對接信義房屋加密端點：
- 條件檢索與分頁清單：/filterObject.php
- 物理實體完整規格詳情：/getObjectContent.php
嚴格落實 SSOT 權限劃分與純數值防腐轉換。
"""

import logging
from typing import Any, Dict, List, Optional

from src.core.exceptions import ResourceNotFoundError
from src.core.interfaces.sale_house import ISaleHouseProvider
from src.domain.common import PageResult
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.query_builder import build_filter_object_payload
from src.providers.source_sinyi.transformers import (
    parse_int,
    transform_sinyi_listing_item,
    transform_sinyi_property_detail,
)

logger = logging.getLogger(__name__)


class SourceSinyiSaleHouseProvider(ISaleHouseProvider):
    """信義房屋中古屋業務領域適配器"""

    def __init__(self, client: SourceSinyiClient):
        self._client = client

    async def search_sale_houses(
        self, query: SaleHouseSearchQuery
    ) -> PageResult[NormalizedSaleListing]:
        """多元條件中古屋搜尋 (/filterObject.php 端點)

        將統一查詢物件轉換為信義房屋篩選酬載，發送雙向加密請求並解析為標準刊登清單。
        """
        # 1. 構建信義封包篩選酬載
        payload = build_filter_object_payload(query)

        # 2. 發送雙向加密請求
        response_json = await self._client.post_encrypted("/filterObject.php", payload)

        # 3. 解析回應資料
        content = response_json.get("content") or {}
        raw_items: List[Dict[str, Any]] = content.get("object") or []

        # 提取總筆數 (信義 totalCnt 可能是字串或整數)
        total_count = parse_int(content.get("totalCnt")) or len(raw_items)

        # 4. 100% 透過純函數轉換為標準刊登規格
        items: List[NormalizedSaleListing] = [
            transform_sinyi_listing_item(obj) for obj in raw_items
        ]

        logger.debug(
            "信義房屋清單檢索成功: 總筆數 %d, 當頁解析 %d 筆",
            total_count,
            len(items),
        )

        return PageResult.create(
            items=items,
            total_records=total_count,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_sale_house_detail(
        self,
        house_id: str,
        summary: Optional[NormalizedSaleListing] = None,
    ) -> NormalizedSalePropertyDetail:
        """根據房屋唯一案號取得完整物件物理詳情 (/getObjectContent.php 端點)

        100% 自詳情 API 解析實體主檔規格，未提供者 100% 純化為 None (SQL NULL)。
        """
        clean_house_id = str(house_id).strip()
        if not clean_house_id:
            raise ResourceNotFoundError("sale_house", house_id)

        # 1. 構建詳情端點請求酬載
        payload = {
            "houseNo": clean_house_id,
            "showOff": 0,
        }

        # 2. 發送雙向加密請求
        response_json = await self._client.post_encrypted("/getObjectContent.php", payload)

        # 3. 檢驗回應內容
        content = response_json.get("content")
        if not content or not isinstance(content, dict) or not content.get("houseNo"):
            raise ResourceNotFoundError("sale_house", clean_house_id)

        # 4. 100% 由詳情 API 轉換為標準實體規格模型
        detail = transform_sinyi_property_detail(content)

        logger.debug(
            "信義房屋詳情解析成功: 案號 %s, 標題 %s, 總價 %d 萬",
            detail.external_house_id,
            detail.title,
            detail.price_wan,
        )

        return detail
