"""HouseLensAPI - 中古屋物件與來源刊登持久化資料表模型 (Property & Listing Models)

純淨強型別規格：所有數值皆以 int / float / bool 存儲，禁止未解析字串與雜質入庫。
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
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
    # 建立此客觀房屋之首要來源身分二元組 (如 591 與 S20604856)
    provider_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_house_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 內部關聯外鍵 (指向 communities 表之主鍵 UUID)
    community_uuid: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("communities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # 外部來源平台社區識別碼 (如 591 社區 ID: '5855864'，客觀保留不可遺失)
    external_community_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    community_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_whole_building: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    price_wan: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 總價 (萬元純整數)
    unit_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 單價 (萬元/坪)
    total_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)  # 總坪數 (純浮點數)

    # 格局數值化規格 (純整數)
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 房數
    living_rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 廳數
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 衛數
    balconies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 陽台數

    # 樓層數值化規格 (純整數，地下室為負數)
    floor_current: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 所在樓層
    floor_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 總樓層

    # 屋齡與費用
    building_age_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)  # 屋齡 (年)
    management_fee_monthly: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 管理費 (元/月)
    public_ratio_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 公設比 (%)
    has_lease: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # 是否帶租約

    # 建築類型與描述
    building_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    structure: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    orientation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parking_desc: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # 產權面積純數值明細 (坪)
    main_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 主建物面積
    auxiliary_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 附屬建物面積
    common_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 共用部分面積
    land_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 土地面積
    parking_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 車位面積

    # 地理位置與座標
    region_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    section_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    street: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # 刊登關聯 (一對多)
    listings: Mapped[List["PropertyListingTable"]] = relationship(
        "PropertyListingTable",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_property_provider_house", "provider_id", "external_house_id"),
        Index("ix_property_dedup", "community_name", "floor_current", "rooms"),
        Index("ix_property_external_community_id", "external_community_id"),
        Index("ix_property_community_uuid", "community_uuid"),
        Index("ix_property_region_section", "region_name", "section_name"),
        Index("ix_property_price_wan", "price_wan"),
        Index("ix_property_building_age_years", "building_age_years"),
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
    listing_price_wan: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 刊登總價 (萬元)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    property: Mapped["PropertyTable"] = relationship(
        "PropertyTable",
        back_populates="listings",
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "external_house_id", name="uq_listing_source"),
    )
