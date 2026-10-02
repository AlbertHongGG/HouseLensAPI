"""HouseLensAPI - 串流同步管線單元測試 (Unit Tests for StreamingSyncPipeline)"""

import pytest
from typing import List, Optional, Set, Tuple
from unittest.mock import AsyncMock

from src.application.streaming_pipeline import (
    PageProcessStats,
    StreamingSyncPipeline,
)
from src.domain.common import PageResult


@pytest.mark.asyncio
async def test_streaming_pipeline_incremental_skip():
    """驗證增量同步時已存在於資料庫的項目會被自動跳過，不觸發詳情 API"""
    # 模擬外部 API：第 1 頁有 10 筆項目 (id_0 ~ id_9)
    async def mock_fetch_page(page: int) -> PageResult[dict]:
        if page == 1:
            items = [{"id": f"id_{i}", "title": f"標題_{i}"} for i in range(10)]
            return PageResult.create(items=items, total_records=10, page=1, page_size=10)
        return PageResult.create(items=[], total_records=10, page=page, page_size=10)

    # 模擬資料庫快篩：id_2, id_4, id_6 已存在
    async def mock_check_existing(ids: List[str]) -> Set[str]:
        return {"id_2", "id_4", "id_6"}

    # 詳情 API 呼叫計數
    detail_call_ids = []

    async def mock_fetch_detail(item: dict) -> Optional[dict]:
        detail_call_ids.append(item["id"])
        return {"detail_info": "ok"}

    # 持久化寫入
    persisted_records = []

    async def mock_persist(pairs: List[Tuple[dict, Optional[dict]]]) -> List[dict]:
        persisted_records.extend(pairs)
        return [{"saved": it["id"]} for it, _ in pairs]

    page_stats_history: List[PageProcessStats] = []

    pipeline = StreamingSyncPipeline[dict, dict, dict](
        fetch_page_func=mock_fetch_page,
        extract_id_func=lambda it: it["id"],
        check_existing_func=mock_check_existing,
        fetch_detail_func=mock_fetch_detail,
        persist_batch_func=mock_persist,
        target_count=10,
    )

    records = await pipeline.execute(on_page_processed=lambda s: page_stats_history.append(s))

    # 驗證總共入庫 7 筆新物件
    assert len(records) == 7
    # 驗證已存在的 3 筆被跳過，詳情 API 只呼叫了 7 次，完全沒有呼叫已存在者
    assert len(detail_call_ids) == 7
    assert "id_2" not in detail_call_ids
    assert "id_4" not in detail_call_ids
    assert "id_6" not in detail_call_ids

    # 驗證單頁回報統計
    assert len(page_stats_history) == 1
    stats = page_stats_history[0]
    assert stats.page == 1
    assert stats.total_in_page == 10
    assert stats.new_count == 7
    assert stats.skipped_count == 3
    assert stats.accumulated_new == 7


@pytest.mark.asyncio
async def test_streaming_pipeline_all_skipped_continues_to_next_page():
    """驗證當整頁均已存在時，零詳情請求並迅速推進至下一頁"""
    # 第 1 頁全部已存在 (id_0 ~ id_4)，第 2 頁有新物件 (id_5 ~ id_9)
    async def mock_fetch_page(page: int) -> PageResult[dict]:
        if page == 1:
            items = [{"id": f"id_{i}"} for i in range(5)]
            return PageResult.create(items=items, total_records=10, page=1, page_size=5)
        elif page == 2:
            items = [{"id": f"id_{i}"} for i in range(5, 10)]
            return PageResult.create(items=items, total_records=10, page=2, page_size=5)
        return PageResult.create(items=[], total_records=10, page=page, page_size=5)

    async def mock_check_existing(ids: List[str]) -> Set[str]:
        # 第 1 頁全部在 DB 內
        return {f"id_{i}" for i in range(5)} & set(ids)

    detail_call_count = 0

    async def mock_fetch_detail(item: dict) -> Optional[dict]:
        nonlocal detail_call_count
        detail_call_count += 1
        return {}

    async def mock_persist(pairs: List[Tuple[dict, Optional[dict]]]) -> List[dict]:
        return [{"saved": it["id"]} for it, _ in pairs]

    page_stats: List[PageProcessStats] = []

    pipeline = StreamingSyncPipeline[dict, dict, dict](
        fetch_page_func=mock_fetch_page,
        extract_id_func=lambda it: it["id"],
        check_existing_func=mock_check_existing,
        fetch_detail_func=mock_fetch_detail,
        persist_batch_func=mock_persist,
        target_count=5,
    )

    records = await pipeline.execute(on_page_processed=lambda s: page_stats.append(s))

    assert len(records) == 5
    # 詳情 API 只對第 2 頁的新物件呼叫了 5 次
    assert detail_call_count == 5

    # 驗證兩頁統計
    assert len(page_stats) == 2
    assert page_stats[0].page == 1
    assert page_stats[0].new_count == 0
    assert page_stats[0].skipped_count == 5
    assert page_stats[1].page == 2
    assert page_stats[1].new_count == 5
    assert page_stats[1].skipped_count == 0


@pytest.mark.asyncio
async def test_streaming_pipeline_target_count_exact_slice():
    """驗證跨頁累加達到目標數量時精確截取並終止"""
    async def mock_fetch_page(page: int) -> PageResult[dict]:
        items = [{"id": f"p{page}_{i}"} for i in range(10)]
        return PageResult.create(items=items, total_records=50, page=page, page_size=10)

    async def mock_check_existing(ids: List[str]) -> Set[str]:
        return set()

    async def mock_fetch_detail(item: dict) -> Optional[dict]:
        return {}

    async def mock_persist(pairs: List[Tuple[dict, Optional[dict]]]) -> List[dict]:
        return [{"saved": it["id"]} for it, _ in pairs]

    pipeline = StreamingSyncPipeline[dict, dict, dict](
        fetch_page_func=mock_fetch_page,
        extract_id_func=lambda it: it["id"],
        check_existing_func=mock_check_existing,
        fetch_detail_func=mock_fetch_detail,
        persist_batch_func=mock_persist,
        target_count=15,  # 要求 15 筆 (第 1 頁 10 筆 + 第 2 頁 5 筆)
    )

    records = await pipeline.execute()
    assert len(records) == 15
