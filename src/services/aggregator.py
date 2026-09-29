"""HouseLensAPI - 房產多源聚合與同步管理服務 (House Aggregator Service)"""

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
        sync_details: bool = False,
        max_items: Optional[int] = None,
    ) -> List[CommunityTable]:
        """從指定 Provider 同步社區資料並持久化至資料庫"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.community.search_communities(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        synced_records: List[CommunityTable] = []
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            for summary in items_to_sync:
                record = await repo.upsert_from_summary(summary, provider_id=provider_id)

                if sync_details:
                    try:
                        detail = await provider.community.get_community_detail(summary.community_id)
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    except Exception as e:
                        logger.warning(
                            f"獲取社區 {summary.community_id} 詳情失敗，保留基本資料: {e}"
                        )

                synced_records.append(record)

        return synced_records

    async def sync_sale_houses(
        self,
        provider_id: str,
        query: SaleHouseSearchQuery,
        sync_details: bool = False,
        max_items: Optional[int] = None,
    ) -> List[PropertyTable]:
        """從指定 Provider 同步中古屋資料，自動透過消歧服務進行去重合併"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.sale_house.search_sale_houses(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        synced_properties: List[PropertyTable] = []
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            for summary in items_to_sync:
                # 評估去重候選
                eval_res = await self.dedup.evaluate_candidate(summary, repo)
                candidate_id = eval_res.matched_property_id if eval_res.is_duplicate else None

                prop = await repo.upsert_from_summary(
                    summary,
                    provider_id=provider_id,
                    candidate_property_id=candidate_id,
                )

                if sync_details:
                    try:
                        detail = await provider.sale_house.get_sale_house_detail(summary.house_id)
                        prop = await repo.upsert_property_with_listing(
                            detail=detail,
                            provider_id=provider_id,
                            summary=summary,
                            candidate_property_id=prop.id,
                        )
                    except Exception as e:
                        logger.warning(
                            f"獲取房屋 {summary.house_id} 詳情失敗，保留清單紀錄: {e}"
                        )

                synced_properties.append(prop)

        return synced_properties

    async def sync_new_houses(
        self,
        provider_id: str,
        query: NewHouseSearchQuery,
        sync_details: bool = False,
        max_items: Optional[int] = None,
    ) -> List[NewHouseTable]:
        """從指定 Provider 同步新建案資料 (含 layout_v2 房型規劃)"""
        provider = self.registry.get_provider(provider_id)
        search_res = await provider.new_house.search_new_houses(query)

        items_to_sync = search_res.items
        if max_items is not None:
            items_to_sync = items_to_sync[:max_items]

        synced_records: List[NewHouseTable] = []
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            for summary in items_to_sync:
                record = await repo.upsert_from_summary(summary, provider_id=provider_id)

                if sync_details:
                    try:
                        detail = await provider.new_house.get_new_house_detail(str(summary.source_hid))
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                    except Exception as e:
                        logger.warning(
                            f"獲取新建案 {summary.source_hid} 詳情失敗，保留基本資料: {e}"
                        )

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

