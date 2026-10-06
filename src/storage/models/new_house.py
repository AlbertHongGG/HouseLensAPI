"""HouseLensAPI - 新建案持久化資料表模型 (New House Table Model)

純淨強型別規格：所有數值皆以 int / float 存儲，禁止未解析字串與雜質入庫。
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Float, Index, Integer, JSON, String, Text, UniqueConstraint
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
    external_project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    housing_status: Mapped[str] = mapped_column(String(64), nullable=False)  # 建案期程狀態 (預售屋/新成屋)
    building_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 建物型態 (住宅大樓/透天等)
    purpose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 法定用途 (住商用/住家用等)
    land_division: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 土地使用分區
    region_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    section_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(256), nullable=False)

    # 時程規劃
    handover_time: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 完工或預計交屋期程
    open_sell_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 公開銷售日期

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

    # 車位純數值與規格規劃
    min_parking_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 車位開價下限 (萬元)
    max_parking_price_wan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 車位開價上限 (萬元)
    parking_ratio_desc: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 車位配比描述
    parking_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 車位配比數值比率
    parking_planning_desc: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 車位規劃描述
    plane_parking_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 平面車位數
    mechanical_parking_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 機械車位數
    charging_piles_desc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 充電設備描述
    has_charging_piles: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # 是否具備充電設備或預留
    parking_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 車位停放型式風格

    # 結構化房型坪數矩陣
    layouts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # 建築描述與工法
    structure: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    orientation: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 建商營造團隊與企劃銷售
    developer_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    builder_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sales_agency_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reception_address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # 社區跨領域關聯
    community_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    external_community_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    community_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    community_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 基地地理座標
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider_id", "external_project_id", name="uq_new_house_source"),
        Index("ix_new_house_region_section", "region_name", "section_name"),
        Index("ix_new_house_lat_lng", "lat", "lng"),
    )
