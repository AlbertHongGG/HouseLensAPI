"""HouseLensAPI - 庫存資料檢索使用案例 (Query Use Case)"""

from typing import List, Optional

from src.storage.database import DatabaseManager, db_manager
from src.storage.models.community import CommunityTable
from src.storage.models.new_house import NewHouseTable
from src.storage.models.property import PropertyTable
from src.storage.repositories.community_repo import CommunityRepository
from src.storage.repositories.new_house_repo import NewHouseRepository
from src.storage.repositories.property_repo import PropertyRepository


class QueryUseCase:
    """在庫多維度房產資料檢索使用案例"""

    def __init__(self, database: DatabaseManager = db_manager):
        self.db = database

    async def list_communities(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        min_age: Optional[float] = None,
        max_age: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityTable]:
        """檢索在庫社區"""
        async with self.db.session() as session:
            repo = CommunityRepository(session)
            return await repo.search(
                region=region,
                section=section,
                keyword=keyword,
                min_age_years=min_age,
                max_age_years=max_age,
                limit=limit,
                offset=offset,
            )

    async def list_properties(
        self,
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_age: Optional[float] = None,
        max_age: Optional[float] = None,
        rooms: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """檢索在庫中古屋客觀實體 (含各平台刊登筆數)"""
        async with self.db.session() as session:
            repo = PropertyRepository(session)
            return await repo.search(
                region_name=region_name,
                section_name=section_name,
                keyword=keyword,
                min_price_wan=min_price,
                max_price_wan=max_price,
                min_age_years=min_age,
                max_age_years=max_age,
                rooms=rooms,
                limit=limit,
                offset=offset,
            )

    async def list_new_houses(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewHouseTable]:
        """檢索在庫新建案"""
        async with self.db.session() as session:
            repo = NewHouseRepository(session)
            return await repo.search(
                region=region,
                section=section,
                keyword=keyword,
                limit=limit,
                offset=offset,
            )
