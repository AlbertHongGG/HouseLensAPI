"""HouseLensAPI - 串流式分頁微批次流水線 (Streaming Page-by-Page Pipeline)

以單一 Page 為不可分割的原子生命週期，實作：
單頁探索 -> 快速快篩已存在 (跳過) -> 僅對新項目併發詳情 -> 立即持久化 Commit -> 即時串流進度回報。
"""

import asyncio
from dataclasses import dataclass
import logging
from typing import (
    Awaitable,
    Callable,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

from src.domain.common import PageResult

logger = logging.getLogger(__name__)

TSummary = TypeVar("TSummary")
TDetail = TypeVar("TDetail")
TRecord = TypeVar("TRecord")


@dataclass
class PageProcessStats:
    """單頁微批次處理狀態統計"""

    page: int
    total_in_page: int
    new_count: int
    skipped_count: int
    accumulated_new: int
    target_count: Optional[int]


class StreamingSyncPipeline(Generic[TSummary, TDetail, TRecord]):
    """通用串流式分頁微批次同步管線

    封裝以「頁」為單位的原子循環與增量跳過機制。
    """

    def __init__(
        self,
        fetch_page_func: Callable[[int], Awaitable[PageResult[TSummary]]],
        extract_id_func: Callable[[TSummary], str],
        check_existing_func: Callable[[List[str]], Awaitable[Set[str]]],
        fetch_detail_func: Callable[[TSummary], Awaitable[Optional[TDetail]]],
        persist_batch_func: Callable[
            [List[Tuple[TSummary, Optional[TDetail]]]], Awaitable[List[TRecord]]
        ],
        target_count: Optional[int] = None,
        concurrency: int = 3,
        max_safety_pages: int = 1000,
    ):
        self.fetch_page_func = fetch_page_func
        self.extract_id_func = extract_id_func
        self.check_existing_func = check_existing_func
        self.fetch_detail_func = fetch_detail_func
        self.persist_batch_func = persist_batch_func
        self.target_count = target_count
        self.concurrency = concurrency
        self.max_safety_pages = max_safety_pages

    async def execute(
        self,
        on_page_processed: Optional[Callable[[PageProcessStats], None]] = None,
        on_item_fetching: Optional[Callable[[str], None]] = None,
        on_item_error: Optional[Callable[[str], None]] = None,
    ) -> List[TRecord]:
        """執行串流微批次同步。

        回傳:
            所有成功入庫的實體紀錄清單。
        """
        all_synced_records: List[TRecord] = []
        page = 1
        sem = asyncio.Semaphore(self.concurrency)

        while True:
            # 安全熔斷檢查
            if page > self.max_safety_pages:
                logger.warning(f"串流分頁同步已達最大安全上限 ({self.max_safety_pages} 頁)，觸發安全熔斷停止。")
                break

            # 1. 探索當前頁清單
            page_res = await self.fetch_page_func(page)
            items = page_res.items or []

            # 終止條件 1: 該頁回傳空列表，代表資料已耗盡
            if not items:
                break

            # 2. 批次快篩已存在於資料庫之外部 ID (跳過已抓取項目)
            external_ids = [self.extract_id_func(it) for it in items]
            existing_ids = await self.check_existing_func(external_ids)

            new_items: List[TSummary] = []
            skipped_items: List[TSummary] = []
            for it in items:
                if self.extract_id_func(it) in existing_ids:
                    skipped_items.append(it)
                else:
                    new_items.append(it)

            # 3. 目標數量截斷檢查
            if self.target_count is not None:
                needed = self.target_count - len(all_synced_records)
                if needed <= 0:
                    break
                if len(new_items) > needed:
                    new_items = new_items[:needed]

            # 4. 併發擷取本頁新物件詳情 (已存在者 0 詳情請求，直接跳過)
            enriched_pairs: List[Tuple[TSummary, Optional[TDetail]]] = []
            if new_items:

                async def enrich_item(item: TSummary) -> Tuple[TSummary, Optional[TDetail]]:
                    async with sem:
                        item_id = self.extract_id_func(item)
                        if on_item_fetching:
                            on_item_fetching(item_id)
                        try:
                            detail = await self.fetch_detail_func(item)
                            return (item, detail)
                        except Exception as e:
                            if on_item_error:
                                on_item_error(f"獲取項目 {item_id} 詳情失敗: {e}")
                            return (item, None)

                enriched_pairs = await asyncio.gather(*(enrich_item(it) for it in new_items))

            # 5. 本頁原子持久化與即時 Commit (寫入 DB)
            saved_records = await self.persist_batch_func(enriched_pairs)
            all_synced_records.extend(saved_records)

            # 6. 回報本頁微批次處理狀態
            stats = PageProcessStats(
                page=page,
                total_in_page=len(items),
                new_count=len(new_items),
                skipped_count=len(skipped_items),
                accumulated_new=len(all_synced_records),
                target_count=self.target_count,
            )
            if on_page_processed is not None:
                on_page_processed(stats)

            # 7. 終止條件檢查
            if self.target_count is not None and len(all_synced_records) >= self.target_count:
                break
            if not page_res.has_next:
                break
            if page_res.total_records > 0 and (page * page_res.page_size) >= page_res.total_records:
                break

            page += 1

        return all_synced_records
