"""HouseLensAPI - 串流同步協調應用案例 (Streaming Sync Use Case)

純淨架構：透過 StreamingSyncPipeline 協調 Provider、去重消歧服務與資料庫，
以「頁 (Page)」為不可分割的原子生命週期，實作：
單頁探索 -> 快速快篩已存在 (跳過) -> 僅對新項目併發詳情 -> 立即持久化 Commit -> 即時串流進度回報。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.application.progress import IProgressReporter, SilentProgressReporter
from src.application.streaming_pipeline import StreamingSyncPipeline
from src.core.registry import ProviderRegistry, registry
from src.domain.community import (
    CommunitySearchQuery,
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.domain.new_house import (
    NewHouseSearchQuery,
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
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
    """協調整合 Providers、消歧去重服務與資料庫之串流同步流水線"""

    def __init__(
        self,
        provider_registry: ProviderRegistry = registry,
        database: DatabaseManager = db_manager,
        dedup_service: Optional[PropertyDeduplicationService] = None,
    ):
        self.registry = provider_registry
        self.db = database
        self.dedup = dedup_service or PropertyDeduplicationService()

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
        """串流式同步社區領域資料 (逐頁快篩跳過、詳情補齊與即時提交)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("社區", current_domain=domain_step, total_domains=domain_total, target_count=max_items)

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.community.search_communities(page_query)

        async def check_existing(ids: List[str]) -> Set[str]:
            async with self.db.session() as session:
                repo = CommunityRepository(session)
                return await repo.filter_existing_external_ids(provider_id, ids)

        async def fetch_detail(summary: NormalizedCommunitySummary) -> Optional[NormalizedCommunityDetail]:
            return await provider.community.get_community_detail(summary.community_id)

        async def persist_batch(
            pairs: List[Tuple[NormalizedCommunitySummary, Optional[NormalizedCommunityDetail]]]
        ) -> List[CommunityTable]:
            saved: List[CommunityTable] = []
            async with self.db.session() as session:
                repo = CommunityRepository(session)
                for item, detail in pairs:
                    if detail is not None:
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    else:
                        record = await repo.upsert_from_summary(item, provider_id=provider_id)
                    saved.append(record)
            return saved

        pipeline = StreamingSyncPipeline[NormalizedCommunitySummary, NormalizedCommunityDetail, CommunityTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: s.community_id,
            check_existing_func=check_existing,
            fetch_detail_func=fetch_detail,
            persist_batch_func=persist_batch,
            target_count=max_items,
            concurrency=concurrency,
        )

        synced: List[CommunityTable] = []
        try:
            synced = await pipeline.execute(
                on_page_processed=rep.on_page_processed,
                on_item_fetching=rep.on_item_fetching,
                on_item_error=rep.on_error,
            )
            rep.on_domain_complete({
                "domain": "社區",
                "total": len(synced),
                "details": len(synced),
                "duplicates": 0,
            })
            return synced
        except (asyncio.CancelledError, KeyboardInterrupt):
            rep.on_interrupted(accumulated_count=len(synced), domain_name="社區")
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
        """串流式同步中古屋資料 (逐頁快篩跳過、詳情補齊與去重消歧即時提交)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("中古屋", current_domain=domain_step, total_domains=domain_total, target_count=max_items)
        dups_count = 0

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.sale_house.search_sale_houses(page_query)

        async def check_existing(ids: List[str]) -> Set[str]:
            async with self.db.session() as session:
                repo = PropertyRepository(session)
                return await repo.filter_existing_external_ids(provider_id, ids)

        async def fetch_detail(summary: NormalizedSaleListing) -> Optional[NormalizedSalePropertyDetail]:
            return await provider.sale_house.get_sale_house_detail(summary.house_id)

        async def persist_batch(
            pairs: List[Tuple[NormalizedSaleListing, Optional[NormalizedSalePropertyDetail]]]
        ) -> List[PropertyTable]:
            nonlocal dups_count
            saved: List[PropertyTable] = []
            async with self.db.session() as session:
                repo = PropertyRepository(session)
                for item, detail in pairs:
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
                    saved.append(prop)
            return saved

        pipeline = StreamingSyncPipeline[NormalizedSaleListing, NormalizedSalePropertyDetail, PropertyTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: s.house_id,
            check_existing_func=check_existing,
            fetch_detail_func=fetch_detail,
            persist_batch_func=persist_batch,
            target_count=max_items,
            concurrency=concurrency,
        )

        synced: List[PropertyTable] = []
        try:
            synced = await pipeline.execute(
                on_page_processed=rep.on_page_processed,
                on_item_fetching=rep.on_item_fetching,
                on_item_error=rep.on_error,
            )
            rep.on_domain_complete({
                "domain": "中古屋",
                "total": len(synced),
                "duplicates": dups_count,
                "details": len(synced),
            })
            return synced
        except (asyncio.CancelledError, KeyboardInterrupt):
            rep.on_interrupted(accumulated_count=len(synced), domain_name="中古屋")
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
        """串流式同步新建案資料 (逐頁快篩跳過、詳情補齊與即時提交)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        rep.on_domain_start("新建案", current_domain=domain_step, total_domains=domain_total, target_count=max_items)

        async def fetch_page(page: int):
            page_query = query.model_copy(update={"page": page})
            return await provider.new_house.search_new_houses(page_query)

        async def check_existing(ids: List[str]) -> Set[str]:
            async with self.db.session() as session:
                repo = NewHouseRepository(session)
                return await repo.filter_existing_external_ids(provider_id, ids)

        async def fetch_detail(summary: NormalizedNewHouseSummary) -> Optional[NormalizedNewHouseDetail]:
            return await provider.new_house.get_new_house_detail(str(summary.source_hid))

        async def persist_batch(
            pairs: List[Tuple[NormalizedNewHouseSummary, Optional[NormalizedNewHouseDetail]]]
        ) -> List[NewHouseTable]:
            saved: List[NewHouseTable] = []
            async with self.db.session() as session:
                repo = NewHouseRepository(session)
                for item, detail in pairs:
                    if detail is not None:
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    else:
                        record = await repo.upsert_from_summary(item, provider_id=provider_id)
                    saved.append(record)
            return saved

        pipeline = StreamingSyncPipeline[NormalizedNewHouseSummary, NormalizedNewHouseDetail, NewHouseTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: str(s.source_hid),
            check_existing_func=check_existing,
            fetch_detail_func=fetch_detail,
            persist_batch_func=persist_batch,
            target_count=max_items,
            concurrency=concurrency,
        )

        synced: List[NewHouseTable] = []
        try:
            synced = await pipeline.execute(
                on_page_processed=rep.on_page_processed,
                on_item_fetching=rep.on_item_fetching,
                on_item_error=rep.on_error,
            )
            rep.on_domain_complete({
                "domain": "新建案",
                "total": len(synced),
                "details": len(synced),
                "duplicates": 0,
            })
            return synced
        except (asyncio.CancelledError, KeyboardInterrupt):
            rep.on_interrupted(accumulated_count=len(synced), domain_name="新建案")
            return synced
