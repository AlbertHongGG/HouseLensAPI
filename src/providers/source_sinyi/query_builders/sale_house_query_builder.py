"""HouseLensAPI - 信義房屋中古屋查詢條件建構器 (Sinyi Sale House Query Builder)

將系統通用 SaleHouseSearchQuery 規範轉換為信義房屋 /filterObject.php 手機端加密端點所需之篩選酬載。
支援郵遞區號映射、價格區間、屋齡區間與排序代碼轉換。
"""

import logging
from typing import Any, Dict, List, Optional

from src.domain.sale_house import SaleHouseSearchQuery
from src.providers.source_sinyi.geo import resolve_sinyi_zipcodes

logger = logging.getLogger(__name__)

# 排序代碼轉換映射
SORT_ORDER_MAP: Dict[str, str] = {
    "default": "default",
    "price_asc": "price-asc",
    "price-asc": "price-asc",
    "price_desc": "price-desc",
    "price-desc": "price-desc",
    "area_asc": "area-asc",
    "area-asc": "area-asc",
    "area_desc": "area-desc",
    "area-desc": "area-desc",
}


class SinyiSaleHouseQueryBuilder:
    """信義房屋中古屋檢索查詢條件建構器"""

    SORT_MAP = SORT_ORDER_MAP

    @classmethod
    def build_search_payload(cls, query: SaleHouseSearchQuery) -> Dict[str, Any]:
        """將 SaleHouseSearchQuery 轉換為信義房屋 /filterObject.php 之完整明文 Request 酬載"""
        region_name = getattr(query, "region_name", None)
        section_name = getattr(query, "section_name", None)
        ret_range = resolve_sinyi_zipcodes(
            region_id=query.region_id,
            region_name=region_name,
            section_name=section_name,
            fallback_all_taiwan=False,
        )

        filter_obj: Dict[str, Any] = {
            "retType": 2,  # 固定為 2 (中古屋買賣)
            "retRange": ret_range,
            "floor": None,
        }

        # 關鍵字
        if query.keywords and query.keywords.strip():
            filter_obj["keyword"] = {"keyword": query.keywords.strip()}

        # 屋齡
        age_ranges = cls.resolve_age_payload(query.min_age_years, query.max_age_years)
        if age_ranges:
            filter_obj["houseAge"] = age_ranges

        # 價格
        price_obj = cls.resolve_price_payload(query.min_price_wan, query.max_price_wan)
        if price_obj:
            filter_obj["price"] = price_obj

        # 排序代碼
        sort_code = "default"
        if query.sort_order and query.sort_order in cls.SORT_MAP:
            sort_code = cls.SORT_MAP[query.sort_order]

        page_num = query.page if query.page and query.page > 0 else 1
        page_size = query.page_size if query.page_size and query.page_size > 0 else 20

        return {
            "page": page_num,
            "pageCnt": page_size,
            "sort": sort_code,
            "filter": filter_obj,
        }

    @classmethod
    def resolve_price_payload(
        cls,
        min_price_wan: Optional[int] = None,
        max_price_wan: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """將總價範圍條件轉換為信義房屋 PriceRequest 物件

        格式: {"priceType": 2, "priceRange": ["{min}-{max}"]}
        """
        if min_price_wan is None and max_price_wan is None:
            return None

        min_p = int(min_price_wan) if min_price_wan is not None else "0"
        max_p = int(max_price_wan) if max_price_wan is not None else "99999"

        return {
            "priceType": 2,
            "priceRange": [f"{min_p}-{max_p}"],
        }

    @classmethod
    def resolve_age_payload(
        cls,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
    ) -> Optional[List[str]]:
        """將屋齡範圍條件轉換為信義房屋 houseAge 清單

        信義支援區間: ["min-5", "5-10", "10-20", "20-30", "30-max"]
        """
        if min_age_years is None and max_age_years is None:
            return None

        min_age = min_age_years if min_age_years is not None else 0.0
        max_age = max_age_years if max_age_years is not None else 999.0

        selected_ranges: List[str] = []
        if min_age < 5.0 and max_age > 0.0:
            selected_ranges.append("min-5")
        if min_age < 10.0 and max_age > 5.0:
            selected_ranges.append("5-10")
        if min_age < 20.0 and max_age > 10.0:
            selected_ranges.append("10-20")
        if min_age < 30.0 and max_age > 20.0:
            selected_ranges.append("20-30")
        if max_age > 30.0:
            selected_ranges.append("30-max")

        return selected_ranges if selected_ranges else None
