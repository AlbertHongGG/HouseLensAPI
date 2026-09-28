"""HouseLensAPI - 資料庫維護與統計使用案例 (Database Maintenance Use Case)"""

import os
from pathlib import Path
from typing import Any, Dict
from sqlalchemy import func, select, text

from src.storage.database import DatabaseManager, db_manager
from src.storage.models.community import CommunityTable
from src.storage.models.new_house import NewHouseTable
from src.storage.models.property import PropertyListingTable, PropertyTable


class DbMaintenanceUseCase:
    """資料庫健康管理、結構初始化與指標統計使用案例"""

    def __init__(self, database: DatabaseManager = db_manager):
        self.db = database

    async def init_db(self) -> None:
        """初始化資料表結構"""
        await self.db.init_db()

    async def get_stats(self) -> Dict[str, Any]:
        """計算庫存容量、實體數量與消歧去重率指標"""
        async with self.db.session() as session:
            # 統計各表數量
            comm_cnt = await session.scalar(select(func.count(CommunityTable.id))) or 0
            prop_cnt = await session.scalar(select(func.count(PropertyTable.id))) or 0
            listing_cnt = await session.scalar(select(func.count(PropertyListingTable.id))) or 0
            nh_cnt = await session.scalar(select(func.count(NewHouseTable.id))) or 0

        # 計算去重合併率
        merged_listings = max(0, listing_cnt - prop_cnt)
        dedup_ratio = (merged_listings / max(listing_cnt, 1)) * 100.0 if listing_cnt > 0 else 0.0

        # 計算檔案大小 (若為本地 SQLite)
        db_size_mb = 0.0
        db_url = self.db.db_url
        if "sqlite" in db_url and "///" in db_url:
            raw_path = db_url.split("///")[-1]
            p = Path(raw_path)
            if p.exists():
                db_size_mb = p.stat().st_size / (1024 * 1024)

        return {
            "db_url": db_url,
            "db_size_mb": db_size_mb,
            "total_communities": comm_cnt,
            "total_properties": prop_cnt,
            "total_listings": listing_cnt,
            "total_new_houses": nh_cnt,
            "merged_listings_count": merged_listings,
            "dedup_ratio_pct": dedup_ratio,
        }

    async def vacuum(self) -> None:
        """執行資料庫重整與空間回收"""
        async with self.db.engine.begin() as conn:
            if "sqlite" in self.db.db_url:
                await conn.execute(text("VACUUM"))
