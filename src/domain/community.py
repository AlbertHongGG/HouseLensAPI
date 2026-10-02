"""HouseLensAPI - 社區核心統一數據規範 (Canonical Community Specifications)

核心層僅定義純淨強型別規格。所有數值皆為純 int / float / bool。
Provider 模組必須自行將外部各平台之字串與特化格式清洗正規化為此規格。
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.domain.common import GeoPoint


class NormalizedCommunitySummary(BaseModel):
    """跨平台統一社區清單摘要規格"""

    community_id: str = Field(..., description="社區唯一代碼")
    community_name: str = Field(..., description="社區名稱")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    full_address: str = Field(..., description="完整地址")
    coordinates: Optional[GeoPoint] = Field(None, description="經緯度座標")
    avg_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="平均單價 (萬元/坪)")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="屋齡 (年)")
    building_type: Optional[str] = Field(None, description="建物型態")
    build_purpose: Optional[str] = Field(None, description="主要用途")
    living_circle_name: Optional[str] = Field(None, description="生活圈商圈名稱")
    nearest_station: Optional[str] = Field(None, description="鄰近捷運站點")
    cover_image_url: Optional[str] = Field(None, description="封面圖片網址")

    @property
    def address(self) -> str:
        return self.full_address

    @property
    def shopping_district(self) -> Optional[str]:
        return self.living_circle_name

    @property
    def transport(self) -> Optional[str]:
        return self.nearest_station


class NormalizedCommunityDetail(BaseModel):
    """跨平台統一社區完整規格 (純數值化)"""

    community_id: str = Field(..., description="社區唯一代號")
    community_name: str = Field(..., description="社區名稱")
    address: str = Field(..., description="社區完整地址")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    coordinates: Optional[GeoPoint] = Field(None, description="經緯度座標")

    # 建築規劃規格 (純數值化)
    avg_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="平均單價 (萬元/坪)")
    total_households: Optional[int] = Field(None, ge=0, description="總戶數純整數 (例如: 290)")
    parking_count: Optional[int] = Field(None, ge=0, description="規劃車位總數純整數 (例如: 152)")
    parking_ratio_pct: Optional[float] = Field(None, ge=0.0, description="車位配比率 (例如: 1.07)")
    public_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="公設比百分比 (例如: 30.0 代表 30%)")
    manage_fee_per_pin: Optional[int] = Field(None, ge=0, description="管理費單價純整數 (單位: 元/坪/月, 例如: 100)")
    base_area_pin: Optional[float] = Field(None, ge=0.0, description="基地總面積純浮點數 (單位: 坪)")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="完工屋齡純浮點數 (單位: 年)")

    # 團隊與工法描述
    building_type: Optional[str] = Field(None, description="建物型態")
    build_purpose: Optional[str] = Field(None, description="主要用途")
    structure: Optional[str] = Field(None, description="建築結構工法 (如: SRC造)")
    direction_rule: Optional[str] = Field(None, description="座向規劃")
    floor_plan_desc: Optional[str] = Field(None, description="樓層規劃描述 (如: 地上24層,地下4層)")
    park_type_str: Optional[str] = Field(None, description="車位型態描述")
    shopping_district: Optional[str] = Field(None, description="生活圈商圈")
    transport: Optional[str] = Field(None, description="鄰近交通站點")
    landscape_name: Optional[str] = Field(None, description="景觀設計")
    postulate_name: Optional[str] = Field(None, description="公設設計")
    facilities: List[str] = Field(default_factory=list, description="公共設施清單")
    developer_company: Optional[str] = Field(None, description="投資興建公司")
    builder_company: Optional[str] = Field(None, description="營造公司")
    architect_company: Optional[str] = Field(None, description="建築設計事務所")

    @property
    def floor_plan(self) -> Optional[str]:
        return self.floor_plan_desc


class CommunitySearchQuery(BaseModel):
    """跨平台統一社區檢索條件規範"""

    region_id: Optional[int] = Field(None, description="標準縣市代碼")
    section_id: Optional[int] = Field(None, description="標準行政區代碼")
    keyword: Optional[str] = Field(None, description="社區名稱或路名關鍵字")
    min_age_years: Optional[float] = Field(None, ge=0.0, description="最小屋齡 (年)")
    max_age_years: Optional[float] = Field(None, ge=0.0, description="最大屋齡 (年)")
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
