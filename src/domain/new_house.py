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


class NewHouseParkingSpec(BaseModel):
    """標準車位規劃與充電設備規格 (純數值化值物件)"""

    parking_price_desc: CleanStr = Field(None, description="車位價格描述 (例如: '155~320萬')")
    min_parking_price_wan: Optional[float] = Field(None, ge=0.0, description="車位價格下限 (萬元)")
    max_parking_price_wan: Optional[float] = Field(None, ge=0.0, description="車位價格上限 (萬元)")
    parking_ratio_desc: CleanStr = Field(None, description="車位配比描述 (例如: '1:0.46')")
    parking_ratio_val: Optional[float] = Field(None, ge=0.0, description="車位配比純數值比率 (例如: 0.46)")
    parking_planning_desc: CleanStr = Field(None, description="車位規劃描述 (例如: '平面式111個、機械式41個')")
    plane_parking_count: Optional[int] = Field(None, ge=0, description="平面車位總數純整數")
    mechanical_parking_count: Optional[int] = Field(None, ge=0, description="機械車位總數純整數")
    charging_piles_desc: CleanStr = Field(None, description="充電設備規劃描述 (例如: '有充電設備（含預留）')")
    has_charging_piles: Optional[bool] = Field(None, description="是否具備充電設備或預留")
    parking_style: CleanStr = Field(None, description="車位型態風格 (例如: '1樓停車', '前院停車')")


class NormalizedNewHouseSummary(BaseModel):
    """跨平台統一新建案清單摘要規格"""

    provider_id: str = Field(..., description="來源平台識別代碼 (如: '591')")
    external_project_id: str = Field(..., description="外部平台建案識別代碼 (如: '138810')")
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

    provider_id: str = Field(..., description="來源平台識別代碼 (如: '591')")
    external_project_id: str = Field(..., description="外部平台建案識別代碼 (如: '138810')")
    project_name: str = Field(..., description="建案名稱")
    build_type: CleanStr = Field(None, description="建案期程狀態 (預售屋/新成屋)")
    building_type: CleanStr = Field(None, description="建物型態 (例如: 住宅大樓, 華廈, 透天)")
    legal_purpose: CleanStr = Field(None, description="法定用途 (例如: 住商用, 住家用)")
    land_division: CleanStr = Field(None, description="土地使用分區 (例如: 第四種商業區)")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    address: str = Field(..., description="基地位置地址")

    # 時程規劃
    handover_time: CleanStr = Field(None, description="完工或預計交屋期程 (例如: '預計2028年第一季度')")
    open_sell_date: CleanStr = Field(None, description="公開銷售日期 (標準日期格式例如: '2025-02-01')")

    # 建築數值化規格
    base_area_pin: Optional[float] = Field(None, ge=0.0, description="基地總面積 (坪)")
    public_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="公設比百分比 (例如: 34.0)")
    total_households: Optional[int] = Field(None, ge=0, description="規劃總戶數純整數 (例如: 290)")
    manage_fee_per_pin: Optional[int] = Field(None, ge=0, description="管理費單價純整數 (元/坪/月, 例如: 150)")
    min_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價下限 (萬元/坪)")
    max_unit_price_wan: Optional[float] = Field(None, ge=0.0, description="開價單價上限 (萬元/坪)")
    min_area_pin: Optional[float] = Field(None, ge=0.0, description="規劃坪數下限 (坪)")
    max_area_pin: Optional[float] = Field(None, ge=0.0, description="規劃坪數上限 (坪)")

    # 車位規格值物件
    parking: NewHouseParkingSpec = Field(default_factory=NewHouseParkingSpec, description="車位規劃與設備規格")

    # 房型坪數規劃矩陣 (純數值結構)
    layouts: List[NewHouseLayoutSpec] = Field(default_factory=list, description="結構化房型坪數清單")

    # 團隊與工法描述
    structural_engine: CleanStr = Field(None, description="建築結構工法")
    direction_rule: CleanStr = Field(None, description="座向規劃")
    developer_company: CleanStr = Field(None, description="投資興建公司")
    builder_company: CleanStr = Field(None, description="營造公司")
    architect_company: CleanStr = Field(None, description="建築設計事務所")
    sales_agency_company: CleanStr = Field(None, description="企劃銷售 / 代銷公司")
    reception_address: CleanStr = Field(None, description="接待會館地址")
    cover_image_url: CleanStr = Field(None, description="封面照片網址")

    # 社區跨領域關聯
    external_community_id: CleanStr = Field(None, description="關聯社區外部識別碼")
    community_name: CleanStr = Field(None, description="關聯社區名稱")
    community_age: Optional[int] = Field(None, ge=0, description="社區屋齡純整數")

    # 地理座標
    latitude: Optional[float] = Field(None, description="基地緯度坐標")
    longitude: Optional[float] = Field(None, description="基地經度坐標")


class NewHouseSearchQuery(BaseSearchQuery):
    """跨平台統一新建案檢索條件規範"""

    is_presale: bool = Field(default=True, description="是否包含預售屋")
    is_new_construction: bool = Field(default=True, description="是否包含新成屋")

