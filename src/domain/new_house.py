"""HouseLensAPI - 新建案核心統一數據規範 (Canonical New House Specifications)

核心層僅定義純淨強型別規格。所有數值皆為純 int / float / bool。
Provider 模組必須自行將外部各平台之字串與特化格式清洗正規化為此規格。
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.domain.common import BaseSearchQuery, CleanStr


class NewHouseLayoutSpec(BaseModel):
    """標準規劃房型與坪數區間項目"""

    room_name: str = Field(..., description="房型名稱 (例如: 一房、二房、三房)")
    rooms_count: Optional[int] = Field(None, ge=1, description="對應房數純整數 (例如: 1, 2, 3)")
    min_area_pin: Optional[float] = Field(None, ge=0.0, description="最低坪數 (例如: 14.0)")
    max_area_pin: Optional[float] = Field(None, ge=0.0, description="最高坪數 (例如: 17.0)")


class NormalizedNewHouseSummary(BaseModel):
    """跨平台統一新建案清單摘要規格"""

    source_hid: int = Field(..., description="建案識別代碼")
    project_name: str = Field(..., description="建案名稱")
    project_status: str = Field(..., description="建案期程狀態 (預售屋/新成屋)")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    address: str = Field(..., description="接待會館或基地地址")
    min_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價下限 (萬元/坪)")
    max_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價上限 (萬元/坪)")
    min_area_pin: Optional[float] = Field(None, ge=0.0, description="規劃坪數下限 (坪)")
    max_area_pin: Optional[float] = Field(None, ge=0.0, description="規劃坪數上限 (坪)")
    developer: CleanStr = Field(None, description="投資興建公司")
    cover_image_url: CleanStr = Field(None, description="封面照片網址")


class NormalizedNewHouseDetail(BaseModel):
    """跨平台統一新建案完整規格 (純數值化)"""

    hid: int = Field(..., description="建案 HID")
    project_name: str = Field(..., description="建案名稱")
    build_type: CleanStr = Field(None, description="建案狀態 (預售屋/新成屋)")
    region: str = Field(..., description="縣市名稱")
    section: str = Field(..., description="行政區名稱")
    address: str = Field(..., description="基地位置地址")

    # 建築數值化規格
    base_area_pin: Optional[float] = Field(None, ge=0.0, description="基地總面積 (坪)")
    public_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="公設比百分比 (例如: 34.0)")
    total_households: Optional[int] = Field(None, ge=0, description="規劃總戶數純整數 (例如: 290)")
    manage_fee_per_pin: Optional[int] = Field(None, ge=0, description="管理費單價純整數 (元/坪/月, 例如: 150)")
    min_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價下限 (萬元/坪)")
    max_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價上限 (萬元/坪)")

    # 房型坪數規劃矩陣 (純數值結構)
    layouts: List[NewHouseLayoutSpec] = Field(default_factory=list, description="結構化房型坪數清單")

    # 團隊與工法描述
    structural_engine: CleanStr = Field(None, description="建築結構工法")
    direction_rule: CleanStr = Field(None, description="座向規劃")
    developer_company: CleanStr = Field(None, description="投資興建公司")
    builder_company: CleanStr = Field(None, description="營造公司")
    architect_company: CleanStr = Field(None, description="建築設計事務所")
    reception_address: CleanStr = Field(None, description="接待會館地址")


class NewHouseSearchQuery(BaseSearchQuery):
    """跨平台統一新建案檢索條件規範"""

    is_presale: bool = Field(default=True, description="是否包含預售屋")
    is_new_construction: bool = Field(default=True, description="是否包含新成屋")

