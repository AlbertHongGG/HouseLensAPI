"""HouseLensAPI - 社區持久化資料表模型 (Community Table Model)"""

import uuid
from typing import Any, List, Optional
from sqlalchemy import JSON, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models.base import Base, TimestampMixin


class CommunityTable(Base, TimestampMixin):
    """標準化社區實體資料表"""

    __tablename__ = "communities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    build_purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    build_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    region_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    section_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    avg_unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit_price_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    shopping_district: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    transport: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # 建築與規劃規格
    age: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    total_households: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    floor_plan: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    structure: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    base_area_ping: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    public_ratio: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    parking_count: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    park_rate: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    park_type_str: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    direction_rule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    build_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    landscape_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    postulate_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    facilities: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # 建商營造團隊與管理
    developer_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    builder_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    management_fee: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        UniqueConstraint("source_provider", "source_id", name="uq_community_source"),
        Index("ix_community_region_section", "region_name", "section_name"),
    )
