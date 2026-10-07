"""HouseLensAPI - 單一物件深度規格組裝使用案例 (Inspect Use Case)"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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

    async def get_community(
        self, identifier: str, provider_id: Optional[str] = None
    ) -> Optional[CommunityTable]:
        """根據內部 UUID、前綴或外部來源代號查詢社區詳情"""
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            # 1. 優先以內部主鍵查詢
            res = await repo.get_by_id(identifier)
            if res is None:
                # 2. 嘗試以前綴比對內部 UUID
                stmt = select(CommunityTable).where(CommunityTable.id.like(f"{identifier}%"))
                q_res = await session.execute(stmt)
                res = q_res.scalars().first()
            if res is None:
                # 3. 嘗試以外部平台專案代碼查詢
                if provider_id:
                    res = await repo.get_by_external_id(provider_id, identifier)
                else:
                    stmt = select(CommunityTable).where(CommunityTable.external_community_id == identifier)
                    q_res = await session.execute(stmt)
                    res = q_res.scalars().first()
            return res

    async def fetch_and_save_community(
        self, provider_id: str, external_community_id: str
    ) -> Optional[CommunityTable]:
        """從指定外部來源即時獲取社區詳情並立即持久化至本地資料庫"""
        from src.core.registry import registry
        provider = registry.get_provider(provider_id)
        detail = await provider.community.get_community_detail(external_community_id)
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            record = await repo.upsert_from_detail(detail, provider_id=provider_id)
            await session.commit()
            return await repo.get_by_id(record.id)

    async def get_property(self, identifier: str) -> Optional[PropertyTable]:
        """根據內部 UUID、前綴或任何平台外部刊登 ID (如 S20604856) 查詢實體與所有比價刊登"""
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            # 1. 優先以內部 UUID 查詢
            res = await repo.get_by_id(identifier)
            if res is None:
                # 2. 嘗試以前綴比對內部 UUID
                stmt = (
                    select(PropertyTable)
                    .options(selectinload(PropertyTable.listings))
                    .where(PropertyTable.id.like(f"{identifier}%"))
                )
                q_res = await session.execute(stmt)
                res = q_res.scalars().first()
            if res is None:
                # 3. 嘗試以主表外部房屋 ID 查詢
                stmt = (
                    select(PropertyTable)
                    .options(selectinload(PropertyTable.listings))
                    .where(
                        PropertyTable.provider_id == "591",
                        PropertyTable.external_house_id == identifier,
                    )
                )
                q_res = await session.execute(stmt)
                res = q_res.scalars().first()
            if res is None:
                # 4. 嘗試以外部刊登編號反查實體
                clean_id = identifier.lstrip("S") if identifier.startswith("S") else identifier
                for ext_id in (identifier, clean_id, f"S{clean_id}"):
                    res = await repo.get_by_listing("591", ext_id)
                    if res:
                        break
            return res

    async def get_new_house(self, identifier: str) -> Optional[NewHouseTable]:
        """根據內部 UUID、前綴或建案外部 ID 查詢新建案詳情 (含 layout_v2)"""
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            # 1. 優先以主鍵 UUID 查詢
            res = await repo.get_by_id(identifier)
            if res is None:
                # 2. 嘗試以前綴比對 UUID
                stmt = select(NewHouseTable).where(NewHouseTable.id.like(f"{identifier}%"))
                q_res = await session.execute(stmt)
                res = q_res.scalars().first()
            if res is None:
                # 3. 嘗試以外部建案 ID 查詢
                res = await repo.get_by_external_id("591", identifier)
            return res
