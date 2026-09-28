"""HouseLensAPI - 全域組態設定管理 (Global Configuration Settings)"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """系統全域組態設定"""

    db_path: str = Field(
        default_factory=lambda: os.getenv("HOUSELENS_DB_PATH", "./houselens.db")
    )
    database_url_override: Optional[str] = Field(
        default_factory=lambda: os.getenv("DATABASE_URL")
    )
    default_provider: str = Field(default="591")
    request_timeout: float = Field(default=15.0)
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    @property
    def database_url(self) -> str:
        """取得最終非同步資料庫連線字串"""
        if self.database_url_override:
            return self.database_url_override
        # 將相對路徑轉換為絕對路徑以確保不同執行目錄下一致
        abs_db_path = Path(self.db_path).resolve().as_posix()
        return f"sqlite+aiosqlite:///{abs_db_path}"


# 全域單例設定實例
settings = Settings()
