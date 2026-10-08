"""HouseLensAPI - 信義房屋社區查詢條件建構器 (Sinyi Community Query Builder)

將標準 CommunitySearchQuery 規範轉換為信義房屋網頁端 /searchCommunity.php 所需之篩選酬載。
支援台灣 22 縣市郵遞區號映射、屋齡範圍轉換、分頁與關鍵字包裝。
"""

import logging
from typing import Any, Dict, List, Optional

from src.domain.community import CommunitySearchQuery
from src.providers.source_sinyi.geo import resolve_sinyi_zipcodes

logger = logging.getLogger(__name__)


class SinyiCommunityQueryBuilder:
    """信義房屋網頁端社區查詢條件建構器"""

    @classmethod
    def build_search_payload(cls, query: CommunitySearchQuery) -> Dict[str, Any]:
        """將 CommunitySearchQuery 轉換為 /searchCommunity.php 請求酬載"""
        filter_dict: Dict[str, Any] = {
            "retType": 2,  # 2: 社區物件
        }

        # 1. 解析行政區與郵遞區號 (retRange，未指定時全台灣)
        region_name = getattr(query, "region_name", None)
        section_name = getattr(query, "section_name", None)
        zipcodes = resolve_sinyi_zipcodes(
            region_id=query.region_id,
            region_name=region_name,
            section_name=section_name,
            fallback_all_taiwan=True,
        )
        if zipcodes:
            filter_dict["retRange"] = zipcodes

        # 2. 關鍵字過濾 (信義網頁端需包裹為 {"keyword": ...})
        if query.keywords and query.keywords.strip():
            filter_dict["keyword"] = {"keyword": query.keywords.strip()}

        # 3. 屋齡條件轉換 (year: "min-10", "10-20", "20-max")
        year_filter = cls.resolve_year_filter(query.min_age_years, query.max_age_years)
        if year_filter:
            filter_dict["year"] = year_filter

        # 4. 組裝頂層分頁與業務參數
        page_num = query.page if query.page and query.page > 0 else 1
        page_size = query.page_size if query.page_size and query.page_size > 0 else 20

        return {
            "page": page_num,
            "pageCnt": page_size,
            "sort": "0",
            "filter": filter_dict,
            "isReturnTotal": True,
        }

    @classmethod
    def resolve_year_filter(
        cls,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
    ) -> Optional[str]:
        """將數值化屋齡條件轉換為信義格式字串 (如 'min-10', '5-15', '30-max')"""
        if min_age_years is None and max_age_years is None:
            return None

        min_str = str(int(min_age_years)) if min_age_years is not None and min_age_years > 0 else "min"
        max_str = str(int(max_age_years)) if max_age_years is not None else "max"

        return f"{min_str}-{max_str}"
