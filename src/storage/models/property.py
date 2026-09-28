"""HouseLensAPI - 中古屋物件與來源刊登持久化資料表模型 (Property & Listing Models)"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models.base import Base, TimestampMixin


class PropertyTable(Base, TimestampMixin):
    """標準化中古屋客觀實體資料表 (經跨來源去重後的標準實體)"""

    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    community_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("communities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    community_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 總價萬元純整數
    unit_price: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    total_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    layout: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    building_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    building_structure: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 核心建築規格
    floor: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    age: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    orientation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    management_fee: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    public_ratio: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    has_lease: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    balcony: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parking_desc: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # 產權面積明細
    main_building_area: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    auxiliary_area: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    common_area: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    land_area: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    parking_area: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 地理位置與座標
    region: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    section: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    street: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 刊登關聯 (一對多)
    listings: Mapped[List["PropertyListingTable"]] = relationship(
        "PropertyListingTable",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_property_dedup", "community_name", "floor", "layout"),
        Index("ix_property_region_section", "region", "section"),
    )


class PropertyListingTable(Base, TimestampMixin):
    """物件刊登來源關聯表 (記錄各平台外部 ID 與刊登詳情)"""

    __tablename__ = "property_listings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    property_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_house_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    listing_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    listing_price: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    property: Mapped["PropertyTable"] = relationship(
        "PropertyTable",
        back_populates="listings",
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "external_house_id", name="uq_listing_source"),
    )
