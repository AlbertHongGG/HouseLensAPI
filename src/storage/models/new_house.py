"""HouseLensAPI - 新建案持久化資料表模型 (New House Table Model)"""

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

    price: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    manage_cost: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    structural_engine: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    park_planning: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    direction_rule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    build_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    park_ratio: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 結構化 layout_v2 房型坪數陣列
    layout_v2: Mapped[Optional[List[Dict[str, str]]]] = mapped_column(JSON, nullable=True)

    unit_price_str: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parking_price_str: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    base_area_ping: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    public_ratio: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    total_households: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    developer_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    builder_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reception_address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    community_id_ref: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider_id", "source_hid", name="uq_new_house_source"),
        Index("ix_new_house_region_section", "region", "section"),
    )
