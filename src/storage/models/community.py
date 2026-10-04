"""HouseLensAPI - 社區持久化資料表模型 (Community Table Model)

純淨強型別規格：所有數值皆以 int / float 存儲，禁止未解析字串與雜質入庫。
"""

import uuid
from typing import List, Optional
from sqlalchemy import Float, Index, Integer, JSON, String, Text, UniqueConstraint
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

    # 純數值行情與規格
    avg_unit_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 平均單價 (萬元/坪)
    building_age_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)  # 屋齡 (年)
    total_households: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 總戶數
    base_area_pin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 基地面積 (坪)
    base_area_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 基地面積純浮點數 (坪)
    public_ratio_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 公設比 (%)
    parking_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 車位數量
    parking_ratio_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 車位配比 (%)
    manage_fee_per_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 管理費單價 (元/坪/月)

    # 描述與規劃資訊
    shopping_district: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    transport: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    floor_plan: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    structure: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    park_type_str: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    park_price: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 車位價格 (萬元)
    land_division: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 土地使用分區
    direction_rule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    landscape_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    postulate_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    facilities: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # 建商營造團隊
    developer_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    builder_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        UniqueConstraint("source_provider", "source_id", name="uq_community_source"),
        Index("ix_community_region_section", "region_name", "section_name"),
        Index("ix_community_building_age_years", "building_age_years"),
    )
