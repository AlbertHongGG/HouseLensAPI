"""HouseLensAPI - 同步協調應用案例 (Sync Use Case)

純淨架構：透過分頁累加器 (PaginationAccumulator) 與結構化進度回報器 (IProgressReporter)，
協調整合 Providers、消歧去重服務與資料庫，執行標準三階段流水線：
1. 清單探索 (跨頁累加收集至目標數量或全量)
2. 併發詳情 (規格補齊，進度條生命週期嚴格封裝)
3. 消歧入庫 (跨來源去重合併與原子寫入)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.application.pagination import PaginationAccumulator
from src.application.progress import IProgressReporter, SilentProgressReporter
from src.core.registry import ProviderRegistry, registry
from src.domain.community import CommunitySearchQuery
from src.domain.new_house import NewHouseSearchQuery
from src.domain.sale_house import SaleHouseSearchQuery
from src.services.deduplication import PropertyDeduplicationService
from src.storage.database import DatabaseManager, db_manager
from src.storage.models.community import CommunityTable
from src.storage.models.new_house import NewHouseTable
from src.storage.models.property import PropertyTable
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.new_house_repo import NewHouseRepository
from src.storage.repositories.property_repo import PropertyRepository

logger = logging.getLogger(__name__)


class SyncUseCase:
    """協調整合 Providers、消歧去重服務與資料庫之同步流水線"""

    def __init__(
        self,
        provider_registry: ProviderRegistry = registry,
        database: DatabaseManager = db_manager,
        dedup_service: Optional[PropertyDeduplicationService] = None,
        accumulator: Optional[PaginationAccumulator] = None,
    ):
        self.registry = provider_registry
        self.db = database
        self.dedup = dedup_service or PropertyDeduplicationService()
        self.accumulator = accumulator or PaginationAccumulator()

    async def sync_communities(
        self,
        provider_id: str,
        query: CommunitySearchQuery,
        max_items: Optional[int] = None,
        concurrency: int = 3,
        reporter: Optional[IProgressReporter] = None,
        domain_step: int = 1,
        domain_total: int = 1,
    ) -> List[CommunityTable]:
        """三階段同步社區領域資料 (清單探索 + 併發詳情補齊 + 消歧入庫)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("社區", current_domain=domain_step, total_domains=domain_total)

        # Stage 1: 分頁探索清單 (累積至目標數量或全量)
        rep.on_discovery_start(target_count=max_items)

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.community.search_communities(page_query)

        items = await self.accumulator.accumulate(
            fetch_page_func=fetch_page,
            target_count=max_items,
            on_page_progress=rep.on_discovery_page,
        )
        rep.on_discovery_complete(len(items))

        if not items:
            rep.on_domain_complete({"domain": "社區", "total": 0, "details": 0, "duplicates": 0})
            return []

        # Stage 2: 併發爬取詳情補齊規格 (進度條生命週期嚴格限制於此區塊)
        tracker = rep.start_enrichment(total=len(items), description="社區詳情補齊")
        sem = asyncio.Semaphore(concurrency)

        async def fetch_detail(item):
            async with sem:
                tracker.advance(item.community_name)
                try:
                    detail = await provider.community.get_community_detail(item.community_id)
                    tracker.enriched(item.community_name)
                    return (item, detail)
                except Exception as e:
                    tracker.on_error(f"獲取社區 {item.community_name} 詳情失敗: {e}")
                    return (item, None)

        enriched_pairs = await asyncio.gather(*(fetch_detail(it) for it in items))
        tracker.close()

        # Stage 3: 持久化入庫
        rep.on_persistence_start()
        synced: List[CommunityTable] = []
        details_count = 0
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            for item, detail in enriched_pairs:
                if detail is not None:
                    record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    details_count += 1
                else:
                    record = await repo.upsert_from_summary(item, provider_id=provider_id)
                synced.append(record)

        rep.on_domain_complete({
            "domain": "社區",
            "total": len(synced),
            "details": details_count,
            "duplicates": 0,
        })
        return synced

    async def sync_sale_houses(
        self,
        provider_id: str,
        query: SaleHouseSearchQuery,
        max_items: Optional[int] = None,
        concurrency: int = 3,
        reporter: Optional[IProgressReporter] = None,
        domain_step: int = 1,
        domain_total: int = 1,
    ) -> List[PropertyTable]:
        """三階段同步中古屋資料 (清單探索 + 併發詳情補齊 + 跨來源去重消歧與刊登合併)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("中古屋", current_domain=domain_step, total_domains=domain_total)

        # Stage 1: 分頁探索清單 (累積至目標數量或全量)
        rep.on_discovery_start(target_count=max_items)

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.sale_house.search_sale_houses(page_query)

        items = await self.accumulator.accumulate(
            fetch_page_func=fetch_page,
            target_count=max_items,
            on_page_progress=rep.on_discovery_page,
        )
        rep.on_discovery_complete(len(items))

        if not items:
            rep.on_domain_complete({"domain": "中古屋", "total": 0, "details": 0, "duplicates": 0})
            return []

        # Stage 2: 併發爬取詳情補齊五大面積與規格 (進度條生命週期嚴格限制於此區塊)
        tracker = rep.start_enrichment(total=len(items), description="中古屋詳情補齊")
        sem = asyncio.Semaphore(concurrency)

        async def fetch_detail(item):
            async with sem:
                tracker.advance(item.title)
                try:
                    detail = await provider.sale_house.get_sale_house_detail(item.house_id)
                    tracker.enriched(item.title)
                    return (item, detail)
                except Exception as e:
                    tracker.on_error(f"獲取房屋 {item.title} 詳情失敗: {e}")
                    return (item, None)

        enriched_pairs = await asyncio.gather(*(fetch_detail(it) for it in items))
        tracker.close()

        # Stage 3: 去重消歧與刊登關係原子化入庫
        rep.on_persistence_start()
        synced: List[PropertyTable] = []
        dups_count = 0
        details_count = 0

        async with self.db.session() as session:
            repo = PropertyRepository(session)
            for item, detail in enriched_pairs:
                if detail is not None:
                    eval_res = await self.dedup.evaluate_candidate(detail, repo)
                    candidate_id = eval_res.matched_property_id if eval_res.is_duplicate else None
                    if eval_res.is_duplicate and candidate_id:
                        dups_count += 1
                        rep.on_item_duplicate(item.title, candidate_id)

                    prop = await repo.upsert_property_with_listing(
                        detail=detail,
                        provider_id=provider_id,
                        summary=item,
                        candidate_property_id=candidate_id,
                    )
                    details_count += 1
                else:
                    eval_res = await self.dedup.evaluate_candidate(item, repo)
                    candidate_id = eval_res.matched_property_id if eval_res.is_duplicate else None
                    if eval_res.is_duplicate and candidate_id:
                        dups_count += 1
                        rep.on_item_duplicate(item.title, candidate_id)

                    prop = await repo.upsert_from_summary(
                        item,
                        provider_id=provider_id,
                        candidate_property_id=candidate_id,
                    )
                synced.append(prop)

        rep.on_domain_complete({
            "domain": "中古屋",
            "total": len(synced),
            "duplicates": dups_count,
            "details": details_count,
        })
        return synced

    async def sync_new_houses(
        self,
        provider_id: str,
        query: NewHouseSearchQuery,
        max_items: Optional[int] = None,
        concurrency: int = 3,
        reporter: Optional[IProgressReporter] = None,
        domain_step: int = 1,
        domain_total: int = 1,
    ) -> List[NewHouseTable]:
        """三階段同步新建案資料 (清單探索 + 併發詳情補齊 + layout_v2 房型規劃)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("新建案", current_domain=domain_step, total_domains=domain_total)

        # Stage 1: 分頁探索清單 (累積至目標數量或全量)
        rep.on_discovery_start(target_count=max_items)

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.new_house.search_new_houses(page_query)

        items = await self.accumulator.accumulate(
            fetch_page_func=fetch_page,
            target_count=max_items,
            on_page_progress=rep.on_discovery_page,
        )
        rep.on_discovery_complete(len(items))

        if not items:
            rep.on_domain_complete({"domain": "新建案", "total": 0, "details": 0, "duplicates": 0})
            return []

        # Stage 2: 併發爬取詳情補齊格局與工程規格 (進度條生命週期嚴格限制於此區塊)
        tracker = rep.start_enrichment(total=len(items), description="新建案詳情補齊")
        sem = asyncio.Semaphore(concurrency)

        async def fetch_detail(item):
            async with sem:
                tracker.advance(item.project_name)
                try:
                    detail = await provider.new_house.get_new_house_detail(str(item.source_hid))
                    tracker.enriched(item.project_name)
                    return (item, detail)
                except Exception as e:
                    tracker.on_error(f"獲取新建案 {item.project_name} 詳情失敗: {e}")
                    return (item, None)

        enriched_pairs = await asyncio.gather(*(fetch_detail(it) for it in items))
        tracker.close()

        # Stage 3: 持久化入庫
        rep.on_persistence_start()
        synced: List[NewHouseTable] = []
        details_count = 0

        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            for item, detail in enriched_pairs:
                if detail is not None:
                    record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    details_count += 1
                else:
                    record = await repo.upsert_from_summary(item, provider_id=provider_id)
                synced.append(record)

        rep.on_domain_complete({
            "domain": "新建案",
            "total": len(synced),
            "details": details_count,
            "duplicates": 0,
        })
        return synced
