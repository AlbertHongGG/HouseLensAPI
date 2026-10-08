"""HouseLensAPI - 信義房屋社區查詢條件建構器 (Sinyi Community Query Builder)

將標準 CommunitySearchQuery 規範轉換為信義房屋網頁端 /searchCommunity.php 所需之篩選酬載。
支援台灣 22 縣市郵遞區號映射、屋齡範圍轉換、分頁與關鍵字包裝。
"""

import logging
from typing import Any, Dict, List, Optional

from src.domain.community import CommunitySearchQuery
from src.domain.enums import Region
from src.providers.source_sinyi.query_builder import TAIWAN_DISTRICT_ZIPCODES

logger = logging.getLogger(__name__)

# 全台灣所有行政區郵遞區號聚合清單 (供未指定縣市時進行全域檢索)
ALL_TAIWAN_ZIPCODES: List[str] = sorted(
    list(set(zipcode for districts in TAIWAN_DISTRICT_ZIPCODES.values() for zipcode in districts.values()))
)


class SinyiCommunityQueryBuilder:
    """信義房屋網頁端社區查詢條件建構器"""

    @classmethod
    def build_search_payload(cls, query: CommunitySearchQuery) -> Dict[str, Any]:
        """將 CommunitySearchQuery 轉換為 /searchCommunity.php 請求酬載"""
        filter_dict: Dict[str, Any] = {
            "retType": 2,  # 2: 社區物件
        }

        # 1. 解析行政區與郵遞區號 (retRange)
        region_name = getattr(query, "region_name", None)
        section_name = getattr(query, "section_name", None)
        zipcodes = cls._resolve_zipcodes(
            region_id=query.region_id,
            region_name=region_name,
            section_name=section_name,
        )
        if zipcodes:
            filter_dict["retRange"] = zipcodes

        # 2. 關鍵字過濾 (信義網頁端需包裹為 {"keyword": ...})
        if query.keywords and query.keywords.strip():
            filter_dict["keyword"] = {"keyword": query.keywords.strip()}

        # 3. 屋齡條件轉換 (year: "min-10", "10-20", "20-max")
        year_filter = cls._resolve_year_filter(query.min_age_years, query.max_age_years)
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
    def _resolve_zipcodes(
        cls,
        region_id: Optional[int],
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
    ) -> List[str]:
        """根據縣市代碼、縣市名稱與行政區名稱解析對應的郵遞區號清單"""
        target_city: Optional[str] = None
        if region_id is not None:
            try:
                target_city = Region.to_chinese_name(region_id)
            except Exception:
                target_city = None

        if not target_city and region_name:
            target_city = region_name.strip()

        # 若未指定縣市，返回全台灣郵遞區號 (避免 retRange 為空造成關鍵字搜尋回傳 0 筆)
        if not target_city or target_city not in TAIWAN_DISTRICT_ZIPCODES:
            return list(ALL_TAIWAN_ZIPCODES)

        city_districts = TAIWAN_DISTRICT_ZIPCODES[target_city]

        # 若有指定特定行政區 (如板橋區)
        if section_name and section_name.strip():
            clean_sec = section_name.strip()
            if clean_sec in city_districts:
                return [city_districts[clean_sec]]
            # 支援部分吻合 (如 "板橋" 匹配 "板橋區")
            for dist_k, dist_zip in city_districts.items():
                if clean_sec in dist_k or dist_k in clean_sec:
                    return [dist_zip]

        # 否則回傳該縣市所有行政區郵遞區號 (排序去重)
        return sorted(list(set(city_districts.values())))

    @classmethod
    def _resolve_year_filter(
        cls, min_age: Optional[float], max_age: Optional[float]
    ) -> Optional[str]:
        """將數值化屋齡條件轉換為信義格式字串 (如 'min-10', '5-15', '30-max')"""
        if min_age is None and max_age is None:
            return None

        min_str = str(int(min_age)) if min_age is not None and min_age > 0 else "min"
        max_str = str(int(max_age)) if max_age is not None else "max"

        return f"{min_str}-{max_str}"
