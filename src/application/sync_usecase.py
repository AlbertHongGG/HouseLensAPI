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
from pydantic import BaseModel, Field, computed_field

from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.new_house_repo import NewHouseRepository
from src.storage.repositories.property_repo import PropertyRepository

logger = logging.getLogger(__name__)


class SyncOptions(BaseModel):
    """跨領域全域同步參數規格 (純淨封裝 CLI/API 發起之同步請求規格)"""

    provider_id: str = Field(default="591", description="來源平台代碼")
    region_id: int = Field(default=1, description="縣市代碼")
    section_id: Optional[int] = Field(default=None, description="行政區代碼")
    keywords: Optional[str] = Field(default=None, description="搜尋關鍵字")
    min_age_years: Optional[float] = Field(default=None, ge=0.0, description="最小屋齡 (年)")
    max_age_years: Optional[float] = Field(default=None, ge=0.0, description="最大屋齡 (年)")
    min_price_wan: Optional[int] = Field(default=None, ge=0, description="最低總價 (萬元)")
    max_price_wan: Optional[int] = Field(default=None, ge=0, description="最高總價 (萬元)")
    is_presale: bool = Field(default=True, description="是否包含預售屋")
    is_new_construction: bool = Field(default=True, description="是否包含新成屋")
    limit: Optional[int] = Field(default=10, description="各領域同步目標筆數 (留空則全量同步)")
    concurrency: int = Field(default=3, ge=1, le=20, description="併發詳情補齊請求數")

    @computed_field
    @property
    def page_size(self) -> int:
        if self.limit and self.limit < 20:
            return self.limit
        return 20


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
            return await provider.community.get_community_detail(summary.external_community_id, summary=summary)

        async def persist_batch(
            pairs: List[Tuple[NormalizedCommunitySummary, Optional[NormalizedCommunityDetail]]]
        ) -> List[CommunityTable]:
            saved: List[CommunityTable] = []
            async with self.db.session() as session:
                repo = CommunityRepository(session)
                for item, detail in pairs:
                    if detail is not None:
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                        saved.append(record)
                    else:
                        logger.warning(f"社區項目 {item.external_community_id} ({item.community_name}) 詳情獲取失敗或已失效，略過入庫。")
            return saved

        pipeline = StreamingSyncPipeline[NormalizedCommunitySummary, NormalizedCommunityDetail, CommunityTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: s.external_community_id,
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
            return await provider.sale_house.get_sale_house_detail(
                summary.external_house_id, summary=summary
            )

        async def persist_batch(
            pairs: List[Tuple[NormalizedSaleListing, Optional[NormalizedSalePropertyDetail]]]
        ) -> List[PropertyTable]:
            nonlocal dups_count
            saved: List[PropertyTable] = []
            async with self.db.session() as session:
                repo = PropertyRepository(session)
                for item, detail in pairs:
                    if detail is not None:
                        # 1. 由領域去重服務全權裁決是否為重複物件
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
                        saved.append(prop)
                    else:
                        logger.warning(f"中古屋房源項目 {item.external_house_id} ({item.title}) 詳情獲取失敗或已失效，略過入庫。")
            return saved

        pipeline = StreamingSyncPipeline[NormalizedSaleListing, NormalizedSalePropertyDetail, PropertyTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: s.external_house_id,
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
            return await provider.new_house.get_new_house_detail(summary.external_project_id)

        async def persist_batch(
            pairs: List[Tuple[NormalizedNewHouseSummary, Optional[NormalizedNewHouseDetail]]]
        ) -> List[NewHouseTable]:
            saved: List[NewHouseTable] = []
            async with self.db.session() as session:
                repo = NewHouseRepository(session)
                for item, detail in pairs:
                    if detail is not None:
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                        saved.append(record)
                    else:
                        logger.warning(f"新建案項目 {item.external_project_id} ({item.project_name}) 詳情獲取失敗或已失效，略過入庫。")
            return saved

        pipeline = StreamingSyncPipeline[NormalizedNewHouseSummary, NormalizedNewHouseDetail, NewHouseTable](
            fetch_page_func=fetch_page,
            extract_id_func=lambda s: s.external_project_id,
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

    async def sync_all(
        self,
        options: SyncOptions,
        reporter: Optional[IProgressReporter] = None,
    ) -> Dict[str, Any]:
        """一鍵串流同步所有領域 (各領域自省吸納自身支援之參數，完全解耦)"""
        rep = reporter or SilentProgressReporter()

        # 1. 社區領域：自省吸納 keywords, min_age_years, max_age_years 等
        comm_query = CommunitySearchQuery.from_options(options)
        communities = await self.sync_communities(
            provider_id=options.provider_id,
            query=comm_query,
            max_items=options.limit,
            concurrency=options.concurrency,
            reporter=rep,
            domain_step=1,
            domain_total=3,
        )

        # 2. 中古屋領域：自省吸納 keywords, min_price_wan, max_price_wan, min_age_years, max_age_years 等
        sale_query = SaleHouseSearchQuery.from_options(options)
        sale_houses = await self.sync_sale_houses(
            provider_id=options.provider_id,
            query=sale_query,
            max_items=options.limit,
            concurrency=options.concurrency,
            reporter=rep,
            domain_step=2,
            domain_total=3,
        )

        # 3. 新建案領域：自省吸納 keywords, is_presale, is_new_construction 等 (自然忽略 age 與 price)
        new_query = NewHouseSearchQuery.from_options(options)
        new_houses = await self.sync_new_houses(
            provider_id=options.provider_id,
            query=new_query,
            max_items=options.limit,
            concurrency=options.concurrency,
            reporter=rep,
            domain_step=3,
            domain_total=3,
        )

        return {
            "communities": communities,
            "sale_houses": sale_houses,
            "new_houses": new_houses,
        }
