"""HouseLensAPI - 單一物件深度規格組裝使用案例 (Inspect Use Case)"""

from typing import Optional

from src.services.deduplication import PropertyDeduplicationService
from src.storage.database import DatabaseManager, db_manager
from src.storage.models.community import CommunityTable
from src.storage.models.new_house import NewHouseTable
from src.storage.models.property import PropertyTable
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.new_house_repo import NewHouseRepository
from src.storage.repositories.property_repo import PropertyRepository


class InspectUseCase:
    """單一房產物件深度組裝與跨平台比價查詢使用案例"""

    def __init__(self, database: DatabaseManager = db_manager):
        self.db = database
        self.dedup = PropertyDeduplicationService()

    async def get_community(
        self, identifier: str, provider_id: Optional[str] = None
    ) -> Optional[CommunityTable]:
        """根據內部 UUID、前綴或外部來源代號查詢社區詳情"""
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            return await repo.find_by_identifier(identifier, provider_id=provider_id)

    async def fetch_and_save_community(
        self, provider_id: str, external_community_id: str
    ) -> Optional[CommunityTable]:
        """從指定外部來源即時獲取社區詳情並立即持久化至本地資料庫"""
        from src.core.registry import registry

        provider = registry.get_provider(provider_id)
        detail = await provider.community.get_community_detail(external_community_id)
        if detail is None:
            return None

        async with self.db.session() as session:
            repo = CommunityRepository(session)
            record = await repo.upsert_from_detail(detail, provider_id=provider_id)
            await session.commit()
            return await repo.get_by_id(record.id)

    async def get_property(
        self, identifier: str, provider_id: Optional[str] = None
    ) -> Optional[PropertyTable]:
        """根據內部 UUID、前綴或任何平台外部刊登 ID (如 S20604856 或 Yungching GUID) 查詢實體與所有比價刊登"""
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            return await repo.find_by_identifier(identifier, provider_id=provider_id)

    async def fetch_and_save_property(
        self, provider_id: str, external_house_id: str
    ) -> Optional[PropertyTable]:
        """從指定外部來源即時獲取中古屋詳情並立即持久化至本地資料庫"""
        from src.core.registry import registry

        provider = registry.get_provider(provider_id)
        detail = await provider.sale_house.get_sale_house_detail(external_house_id)
        if detail is None:
            return None

        async with self.db.session() as session:
            repo = PropertyRepository(session)
            eval_res = await self.dedup.evaluate_candidate(detail, repo)
            candidate_id = eval_res.matched_property_id if eval_res.is_duplicate else None
            record = await repo.upsert_property_with_listing(
                detail=detail,
                provider_id=provider_id,
                candidate_property_id=candidate_id,
            )
            await session.commit()
            return await repo.get_by_id(record.id)

    async def get_new_house(
        self, identifier: str, provider_id: Optional[str] = None
    ) -> Optional[NewHouseTable]:
        """根據內部 UUID、前綴或建案外部 ID 查詢新建案詳情 (含 layout_v2)"""
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            return await repo.find_by_identifier(identifier, provider_id=provider_id)
