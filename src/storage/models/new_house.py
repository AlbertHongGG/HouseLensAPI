"""HouseLensAPI - 新建案持久化資料表模型 (New House Table Model)

純淨強型別規格：所有數值皆以 int / float 存儲，禁止未解析字串與雜質入庫。
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models.base import Base, TimestampMixin


class NewHouseTable(Base, TimestampMixin):
    """標準化新建案實體資料表"""

    __tablename__ = "new_houses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    provider_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_hid: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    project_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    build_type: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(256), nullable=False)

    # 開價與坪數純數值區間
    min_unit_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 開價單價下限 (萬元/坪)
    max_unit_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 開價單價上限 (萬元/坪)
    min_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 坪數下限 (坪)
    max_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 坪數上限 (坪)

    # 建築純數值規格
    base_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 基地面積 (坪)
    public_ratio_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 公設比 (%)
    total_households: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 總戶數
    manage_fee_per_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 管理費 (元/坪/月)

    # 結構化房型坪數矩陣
    layouts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # 建築描述與工法
    structural_engine: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    direction_rule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 建商營造團隊
    developer_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    builder_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reception_address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider_id", "source_hid", name="uq_new_house_source"),
        Index("ix_new_house_region_section", "region", "section"),
    )
