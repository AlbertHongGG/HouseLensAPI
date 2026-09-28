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

from src.storage.models.base import Base

DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///houselens.db")


class DatabaseManager:
    """非同步資料庫連線與 Session 生命週期管理器"""

    def __init__(self, db_url: str = DEFAULT_DB_URL, echo: bool = False):
        self.db_url = db_url
        self.echo = echo
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

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

    async def init_db(self) -> None:
        """非同步初始化資料庫，建立所有尚未建立之資料表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        """非同步清空資料庫，供測試或重置使用"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """取得具備交易自動管理之非同步 Session context manager"""
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
