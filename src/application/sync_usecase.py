"""HouseLensAPI - 資料同步使用案例 (Sync Use Case)"""

import logging
from typing import Any, Dict, List, Optional

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
        reporter: Optional[IProgressReporter] = None,
    ) -> List[CommunityTable]:
        """同步社區領域資料並驅動進度回報"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        search_res = await provider.community.search_communities(query)
        items = search_res.items[:max_items] if max_items else search_res.items
        rep.on_start(domain="社區", total=len(items))

        synced: List[CommunityTable] = []
        details_count = 0

        async with self.db.session() as session:
            repo = CommunityRepository(session)
            for item in items:
                record = await repo.upsert_from_summary(item, provider_id=provider_id)
                rep.on_item_fetched(item.community_name)

                if sync_details:
                    try:
                        detail = await provider.community.get_community_detail(item.community_id)
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                        details_count += 1
                        rep.on_item_detail_enriched(item.community_name)
                    except Exception as e:
                        rep.on_error(f"獲取社區 {item.community_name} 詳情失敗: {e}")

                synced.append(record)

        rep.on_complete({"total": len(synced), "details": details_count, "duplicates": 0})
        return synced

    async def sync_sale_houses(
        self,
        provider_id: str,
        query: SaleHouseSearchQuery,
        sync_details: bool = False,
        max_items: Optional[int] = None,
        reporter: Optional[IProgressReporter] = None,
    ) -> List[PropertyTable]:
        """同步中古屋資料 (含跨來源去重消歧與刊登合併)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        search_res = await provider.sale_house.search_sale_houses(query)
        items = search_res.items[:max_items] if max_items else search_res.items
        rep.on_start(domain="中古屋", total=len(items))

        synced: List[PropertyTable] = []
        dups_count = 0
        details_count = 0

        async with self.db.session() as session:
            repo = PropertyRepository(session)
            for item in items:
                # 執行消歧去重評估
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
                rep.on_item_fetched(item.title)

                if sync_details:
                    try:
                        detail = await provider.sale_house.get_sale_house_detail(item.house_id)
                        prop = await repo.upsert_property_with_listing(
                            detail=detail,
                            provider_id=provider_id,
                            summary=item,
                            candidate_property_id=prop.id,
                        )
                        details_count += 1
                        rep.on_item_detail_enriched(item.title)
                    except Exception as e:
                        rep.on_error(f"獲取房屋 {item.title} 詳情失敗: {e}")

                synced.append(prop)

        rep.on_complete({"total": len(synced), "duplicates": dups_count, "details": details_count})
        return synced

    async def sync_new_houses(
        self,
        provider_id: str,
        query: NewHouseSearchQuery,
        sync_details: bool = False,
        max_items: Optional[int] = None,
        reporter: Optional[IProgressReporter] = None,
    ) -> List[NewHouseTable]:
        """同步新建案資料 (含 layout_v2 房型規劃)"""
        rep = reporter or SilentProgressReporter()
        provider = self.registry.get_provider(provider_id)

        search_res = await provider.new_house.search_new_houses(query)
        items = search_res.items[:max_items] if max_items else search_res.items
        rep.on_start(domain="新建案", total=len(items))

        synced: List[NewHouseTable] = []
        details_count = 0

        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            for item in items:
                record = await repo.upsert_from_summary(item, provider_id=provider_id)
                rep.on_item_fetched(item.project_name)

                if sync_details:
                    try:
                        detail = await provider.new_house.get_new_house_detail(str(item.source_hid))
                        record = await repo.upsert_from_detail(detail, provider_id=provider_id)
                        details_count += 1
                        rep.on_item_detail_enriched(item.project_name)
                    except Exception as e:
                        rep.on_error(f"獲取新建案 {item.project_name} 詳情失敗: {e}")

                synced.append(record)

        rep.on_complete({"total": len(synced), "details": details_count, "duplicates": 0})
        return synced
