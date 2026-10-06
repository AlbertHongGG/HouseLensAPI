"""HouseLensAPI - 非同步資料庫連線與 Session 管理 (Async Database Manager)"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings
from src.storage.models.base import Base


class DatabaseManager:
    """非同步資料庫連線與 Session 生命週期管理器"""

    def __init__(self, db_url: Optional[str] = None, echo: bool = False):
        self._db_url = db_url
        self.echo = echo
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
        self._schema_checked: bool = False

    @property
    def db_url(self) -> str:
        """取得目前連線字串"""
        return self._db_url or settings.database_url

    def configure(self, db_url: str, echo: Optional[bool] = None) -> None:
        """動態重新配置資料庫連線字串"""
        self._db_url = db_url
        if echo is not None:
            self.echo = echo
        self._engine = None
        self._sessionmaker = None
        self._schema_checked = False

    @property
    def engine(self) -> AsyncEngine:
        """取得或建立 AsyncEngine"""
        if self._engine is None:
            self._engine = create_async_engine(
                self.db_url,
                echo=self.echo,
                future=True,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """取得或建立 async_sessionmaker"""
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return self._sessionmaker

    @staticmethod
    def _migrate_sqlite_columns(connection) -> None:
        """針對既有 SQLite 資料表執行輕量安全欄位增補 (Auto-migration)"""
        from sqlalchemy import inspect, text

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        if "properties" in tables:
            cols = {col["name"] for col in inspector.get_columns("properties")}
            if "cover_image_url" not in cols:
                connection.execute(text("ALTER TABLE properties ADD COLUMN cover_image_url VARCHAR(1000)"))
            if "image_urls" not in cols:
                connection.execute(text("ALTER TABLE properties ADD COLUMN image_urls JSON"))

        if "property_listings" in tables:
            cols = {col["name"] for col in inspector.get_columns("property_listings")}
            if "cover_image_url" not in cols:
                connection.execute(text("ALTER TABLE property_listings ADD COLUMN cover_image_url VARCHAR(1000)"))
            if "image_urls" not in cols:
                connection.execute(text("ALTER TABLE property_listings ADD COLUMN image_urls JSON"))

    async def init_db(self) -> None:
        """非同步初始化資料庫，建立所有尚未建立之資料表並進行輕量結構補齊"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(self._migrate_sqlite_columns)
        self._schema_checked = True

    async def drop_all(self) -> None:
        """非同步清空資料庫，供測試或重置使用"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """取得具備交易自動管理之非同步 Session context manager"""
        if not self._schema_checked:
            await self.init_db()

        async with self.session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    async def close(self) -> None:
        """釋放連線池資源"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


# 預設單例執行個體
db_manager = DatabaseManager()
