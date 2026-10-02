"""HouseLensAPI - 通用領域分頁累加器 (Pagination Accumulator)

封裝跨頁資料探索與數量累積策略，徹底解耦 Provider 單頁查詢與業務累積需求。
支援目標數量精準截斷、全量遍歷與防死迴圈之安全熔斷機制。
"""

import logging
from typing import Awaitable, Callable, Generic, List, Optional, TypeVar

from src.domain.common import PageResult

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 頁面探索回報回呼簽章: (page_num, current_page_items_count, accumulated_so_far, target_count)
PageProgressCallback = Callable[[int, int, int, Optional[int]], None]


class PaginationAccumulator(Generic[T]):
    """通用強型別分頁累加器

    負責協調外部 Provider 逐頁擷取資料，並依目標筆數或全量模式進行累積。
    """

    def __init__(self, default_page_size: int = 20, max_safety_pages: int = 1000):
        self.default_page_size = default_page_size
        self.max_safety_pages = max_safety_pages

    async def accumulate(
        self,
        fetch_page_func: Callable[[int], Awaitable[PageResult[T]]],
        target_count: Optional[int] = None,
        on_page_progress: Optional[PageProgressCallback] = None,
    ) -> List[T]:
        """執行跨頁累加探索。

        參數:
            fetch_page_func: 接收頁碼 (從 1 開始) 並回傳 PageResult[T] 的非同步函式。
            target_count: 目標抓取筆數。若為 None 則持續翻頁抓取全部可用資料。
            on_page_progress: 每完成一頁抓取時之進度回報回呼。

        回傳:
            收集並符合數量要求之標準實體列表。
        """
        accumulated: List[T] = []
        page = 1

        while True:
            # 安全熔斷機制: 避免異常 API 造成無限死迴圈
            if page > self.max_safety_pages:
                logger.warning(f"分頁累加已達最大安全上限 ({self.max_safety_pages} 頁)，觸發安全熔斷停止。")
                break

            page_res = await fetch_page_func(page)
            items = page_res.items or []

            # 終止條件 1: 該頁回傳空列表，代表資料已耗盡
            if not items:
                break

            accumulated.extend(items)

            # 觸發進度回報
            if on_page_progress is not None:
                on_page_progress(page, len(items), len(accumulated), target_count)

            # 終止條件 2: 指定 target_count 且累計數量已達標，精確截斷
            if target_count is not None and len(accumulated) >= target_count:
                accumulated = accumulated[:target_count]
                break

            # 終止條件 3: 外部資料來源已明確標示無下一頁，或累計數量已達總筆數
            if not page_res.has_next:
                break
            if page_res.total_records > 0 and len(accumulated) >= page_res.total_records:
                break

            page += 1

        return accumulated
