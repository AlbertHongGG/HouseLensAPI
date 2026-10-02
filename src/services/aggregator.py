import asyncio
import logging
from typing import List, Optional

import src.providers  # 自動載入並註冊內建 providers
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


class HouseAggregatorService:
    """全網房產資料聚合管理服務 (協調整合 Providers、去重模組與持久化倉儲)"""

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
    ) -> List[CommunityTable]:
        """兩階段社區資料同步管線 (清單探索 + 併發詳情補齊 + 入庫)"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.community.search_communities(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        # Stage 2: 併發爬取詳情補齊規格
        sem = asyncio.Semaphore(concurrency)

        async def fetch_community_detail(summary):
            async with sem:
                try:
                    detail = await provider.community.get_community_detail(summary.community_id)
                    return (summary, detail)
                except Exception as e:
                    logger.warning(f"獲取社區 {summary.community_id} 詳情失敗: {e}")
                    return (summary, None)

        enriched_pairs = await asyncio.gather(
            *(fetch_community_detail(item) for item in items_to_sync)
        )

        # Stage 3: 持久化入庫
        synced_records: List[CommunityTable] = []
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            for summary, detail in enriched_pairs:
                if detail is not None:
                    record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                else:
                    record = await repo.upsert_from_summary(summary, provider_id=provider_id)
                synced_records.append(record)

        return synced_records

    async def sync_sale_houses(
        self,
        provider_id: str,
        query: SaleHouseSearchQuery,
        max_items: Optional[int] = None,
        concurrency: int = 3,
    ) -> List[PropertyTable]:
        """兩階段中古屋資料同步管線 (清單探索 + 併發詳情補齊 + 純數值去重消歧與刊登合併)"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.sale_house.search_sale_houses(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        # Stage 2: 併發爬取詳情補齊五大面積與建築規格
        sem = asyncio.Semaphore(concurrency)

        async def fetch_house_detail(summary):
            async with sem:
                try:
                    detail = await provider.sale_house.get_sale_house_detail(summary.house_id)
                    return (summary, detail)
                except Exception as e:
                    logger.warning(f"獲取房屋 {summary.house_id} 詳情失敗: {e}")
                    return (summary, None)

        enriched_pairs = await asyncio.gather(
            *(fetch_house_detail(item) for item in items_to_sync)
        )

        # Stage 3: 去重消歧與刊登關係原子化入庫
        synced_properties: List[PropertyTable] = []
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            for summary, detail in enriched_pairs:
                if detail is not None:
                    prop = await repo.upsert_property_with_listing(
                        detail=detail,
                        provider_id=provider_id,
                        summary=summary,
                    )
                else:
                    eval_res = await self.dedup.evaluate_candidate(summary, repo)
                    candidate_id = eval_res.matched_property_id if eval_res.is_duplicate else None
                    prop = await repo.upsert_from_summary(
                        summary,
                        provider_id=provider_id,
                        candidate_property_id=candidate_id,
                    )
                synced_properties.append(prop)

        return synced_properties

    async def sync_new_houses(
        self,
        provider_id: str,
        query: NewHouseSearchQuery,
        max_items: Optional[int] = None,
        concurrency: int = 3,
    ) -> List[NewHouseTable]:
        """兩階段新建案資料同步管線 (清單探索 + 併發詳情補齊 + layout_v2 房型規格入庫)"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.new_house.search_new_houses(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        # Stage 2: 併發爬取詳情補齊格局與工程規格
        sem = asyncio.Semaphore(concurrency)

        async def fetch_new_house_detail(summary):
            async with sem:
                try:
                    detail = await provider.new_house.get_new_house_detail(str(summary.source_hid))
                    return (summary, detail)
                except Exception as e:
                    logger.warning(f"獲取新建案 {summary.source_hid} 詳情失敗: {e}")
                    return (summary, None)

        enriched_pairs = await asyncio.gather(
            *(fetch_new_house_detail(item) for item in items_to_sync)
        )

        # Stage 3: 持久化入庫
        synced_records: List[NewHouseTable] = []
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            for summary, detail in enriched_pairs:
                if detail is not None:
                    record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                else:
                    record = await repo.upsert_from_summary(summary, provider_id=provider_id)
                synced_records.append(record)

        return synced_records


    async def search_communities(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityTable]:
        """在庫社區跨條件檢索"""
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            return await repo.search(
                region=region,
                section=section,
                keyword=keyword,
                min_age_years=min_age_years,
                max_age_years=max_age_years,
                limit=limit,
                offset=offset,
            )

    async def search_properties(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        rooms: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """在庫中古屋物件跨條件檢索 (含屋齡與房數篩選)"""
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            return await repo.search(
                region=region,
                section=section,
                keyword=keyword,
                min_price_wan=min_price,
                max_price_wan=max_price,
                min_age_years=min_age_years,
                max_age_years=max_age_years,
                rooms=rooms,
                limit=limit,
                offset=offset,
            )

    async def search_new_houses(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewHouseTable]:
        """在庫新建案跨條件檢索"""
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            return await repo.search(
                region=region,
                section=section,
                keyword=keyword,
                limit=limit,
                offset=offset,
            )

