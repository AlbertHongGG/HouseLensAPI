"""HouseLensAPI - 社區核心統一數據規範 (Canonical Community Specifications)

核心層僅定義純淨強型別規格。所有數值皆為純 int / float / bool。
Provider 模組必須自行將外部各平台之字串與特化格式清洗正規化為此規格。
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.common import BaseSearchQuery, GeoPoint


class NormalizedCommunitySummary(BaseModel):
    """跨平台統一社區清單摘要規格"""

    community_id: str = Field(..., description="社區唯一代碼")
    community_name: str = Field(..., description="社區名稱")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    full_address: str = Field(..., description="完整地址")
    coordinates: Optional[GeoPoint] = Field(None, description="經緯度座標")
    avg_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="成交均價 (萬元/坪)")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="屋齡 (年)")
    # 三維正交解耦欄位
    building_type: Optional[str] = Field(None, description="建物實體型態 (如: 住宅大樓、華廈、公寓、透天)")
    build_purpose: Optional[str] = Field(None, description="主要用途 (如: 住宅、商辦)")
    housing_status: Optional[str] = Field(None, description="成屋/建案狀態 (如: 預售屋、新成屋、中古屋)")
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
    avg_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="成交均價 (萬元/坪)")
    total_households: Optional[int] = Field(None, ge=0, description="總戶數純整數 (例如: 290)")
    parking_count: Optional[int] = Field(None, ge=0, description="規劃車位總數純整數 (例如: 152)")
    parking_ratio_pct: Optional[float] = Field(None, ge=0.0, description="車位配比率 (例如: 1.07)")
    public_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="公設比百分比 (例如: 30.0 代表 30%)")
    manage_fee_per_pin: Optional[int] = Field(None, ge=0, description="管理費單價純整數 (單位: 元/坪/月, 例如: 100)")
    base_area_num: Optional[float] = Field(None, ge=0.0, description="基地總面積純浮點數 (單位: 坪)")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="完工屋齡純浮點數 (單位: 年)")

    # 團隊與工法描述 (三維正交設計)
    building_type: Optional[str] = Field(None, description="建物實體型態 (如: 住宅大樓、華廈、公寓、透天)")
    build_purpose: Optional[str] = Field(None, description="法定使用用途 (如: 住家用、住商用、商業用)")
    housing_status: Optional[str] = Field(None, description="成屋/建案狀態 (如: 預售屋、新成屋、中古屋)")
    structure: Optional[str] = Field(None, description="建築結構工法 (如: SRC造)")
    direction_rule: Optional[str] = Field(None, description="座向規劃")
    floor_plan_desc: Optional[str] = Field(None, description="樓層規劃描述 (如: 地上24層,地下4層)")
    park_type_str: Optional[str] = Field(None, description="車位型態描述")
    park_price: Optional[str] = Field(None, description="車位價格描述 (如: 290~330萬)")
    land_division: Optional[str] = Field(None, description="土地使用分區 (如: 第三種住宅區)")
    shopping_district: Optional[str] = Field(None, description="生活圈商圈")
    transport: Optional[str] = Field(None, description="鄰近交通站點")
    landscape_name: Optional[str] = Field(None, description="景觀設計")
    postulate_name: Optional[str] = Field(None, description="公設設計")
    cover_image_url: Optional[str] = Field(None, description="封面圖片網址")
    facilities: List[str] = Field(default_factory=list, description="公共設施清單")
    developer_company: Optional[str] = Field(None, description="投資興建公司")
    builder_company: Optional[str] = Field(None, description="營造公司")
    architect_company: Optional[str] = Field(None, description="建築設計事務所")

    @property
    def base_area_pin(self) -> Optional[float]:
        return self.base_area_num

    @property
    def floor_plan(self) -> Optional[str]:
        return self.floor_plan_desc


class CommunitySearchQuery(BaseSearchQuery):
    """跨平台統一社區檢索條件規範"""

    min_age_years: Optional[float] = Field(None, ge=0.0, description="最小屋齡 (年)")
    max_age_years: Optional[float] = Field(None, ge=0.0, description="最大屋齡 (年)")
