"""HouseLensAPI - 分頁累加器單元測試 (Unit Tests for Pagination Accumulator)"""

import pytest
from src.application.pagination import PaginationAccumulator
from src.domain.common import PageResult


@pytest.mark.asyncio
async def test_pagination_accumulator_target_count_exact_slice():
    """驗證當指定目標筆數時，能跨頁累積並精準截取至目標數量"""
    accumulator = PaginationAccumulator[dict](default_page_size=20)

    # 模擬外部 API：每頁 20 筆，共 3 頁 (60 筆)
    async def mock_fetch(page: int) -> PageResult[dict]:
        items = [{"id": f"item_{(page - 1) * 20 + i}"} for i in range(20)]
        return PageResult.create(items=items, total_records=60, page=page, page_size=20)

    # 要求 30 筆 (第 1 頁 20 筆 + 第 2 頁前 10 筆)
    progress_records = []

    def on_progress(p, cur_count, acc_count, target):
        progress_records.append((p, cur_count, acc_count, target))

    result = await accumulator.accumulate(
        fetch_page_func=mock_fetch,
        target_count=30,
        on_page_progress=on_progress,
    )

    assert len(result) == 30
    assert result[0]["id"] == "item_0"
    assert result[29]["id"] == "item_29"
    # 進度記錄應有 2 頁
    assert len(progress_records) == 2
    assert progress_records[0] == (1, 20, 20, 30)
    assert progress_records[1] == (2, 20, 40, 30)


@pytest.mark.asyncio
async def test_pagination_accumulator_unlimited_mode():
    """驗證當未指定目標筆數 (None) 時，持續翻頁直至無下一頁"""
    accumulator = PaginationAccumulator[dict]()

    # 模擬外部 API：第 1 頁 15 筆，第 2 頁 10 筆，總共 25 筆
    async def mock_fetch(page: int) -> PageResult[dict]:
        if page == 1:
            items = [{"id": f"p1_{i}"} for i in range(15)]
            return PageResult.create(items=items, total_records=25, page=1, page_size=15)
        elif page == 2:
            items = [{"id": f"p2_{i}"} for i in range(10)]
            return PageResult.create(items=items, total_records=25, page=2, page_size=15)
        else:
            return PageResult.create(items=[], total_records=25, page=page, page_size=15)

    result = await accumulator.accumulate(fetch_page_func=mock_fetch, target_count=None)

    assert len(result) == 25
    assert result[0]["id"] == "p1_0"
    assert result[24]["id"] == "p2_9"


@pytest.mark.asyncio
async def test_pagination_accumulator_stops_on_empty_page():
    """驗證當遭遇空資料頁時自動安全中斷"""
    accumulator = PaginationAccumulator[dict]()

    async def mock_fetch(page: int) -> PageResult[dict]:
        return PageResult.create(items=[], total_records=100, page=page, page_size=20)

    result = await accumulator.accumulate(fetch_page_func=mock_fetch, target_count=50)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_pagination_accumulator_safety_circuit_breaker():
    """驗證安全熔斷機制防止無限翻頁"""
    accumulator = PaginationAccumulator[dict](max_safety_pages=3)

    call_count = 0

    # 模擬惡意/異常 API 永遠宣稱有下一頁且回傳重複項目
    async def infinite_mock(page: int) -> PageResult[dict]:
        nonlocal call_count
        call_count += 1
        return PageResult.create(items=[{"id": f"infinite_{page}"}], total_records=999999, page=page, page_size=1)

    result = await accumulator.accumulate(fetch_page_func=infinite_mock, target_count=9999)
    # 應在請求完第 3 頁後，於第 4 頁檢查 page > max_safety_pages 時熔斷停止
    assert call_count == 3
    assert len(result) == 3
