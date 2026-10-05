"""HouseLensAPI - 中古屋核心統一數據規範 (Canonical Sale House Specifications)

核心層僅定義純淨強型別規格。所有數值皆為純 int / float / bool。
Provider 模組必須自行將外部各平台之字串與特化格式清洗正規化為此規格。
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.domain.common import BaseSearchQuery, CleanStr, GeoPoint


class NormalizedSaleListing(BaseModel):
    """跨平台統一中古屋刊登廣告規格 (各平台房仲/屋主之一筆刊登)"""

    provider_id: str = Field(..., description="來源平台識別代碼 (如: '591', 'sinyi', 'yungching')")
    external_house_id: str = Field(..., description="外部平台房源唯一代號 (如: 'S20604856')")
    title: str = Field(..., description="物件刊登標題")
    price_wan: int = Field(..., ge=0, description="刊登開價純整數 (單位: 萬元)")
    unit_price_wan: Optional[float] = Field(None, ge=0.0, description="每坪單價浮點數 (單位: 萬元/坪)")
    total_area_pin: float = Field(..., ge=0.0, description="權狀登記總坪數 (單位: 坪)")

    # 物理結構數值化規格 (由 Provider 模組自行正規化)
    floor_current: Optional[int] = Field(None, description="所在樓層純整數 (如: 2)")
    floor_total: Optional[int] = Field(None, description="總樓層數純整數 (如: 24)")
    rooms: Optional[int] = Field(None, ge=0, description="房數純整數 (如: 3)")
    living_rooms: Optional[int] = Field(None, ge=0, description="廳數純整數 (如: 2)")
    bathrooms: Optional[int] = Field(None, ge=0, description="衛數純整數 (如: 2)")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="完工屋齡浮點數 (單位: 年, 如: 1.0, 0.25)")

    # 分類與地理位置
    building_type: CleanStr = Field(None, description="建物型態 (如: 住宅、辦公)")
    is_whole_building: bool = Field(default=False, description="是否為整棟銷售 (如透天、整棟別墅)")
    region_name: str = Field(..., description="縣市名稱 (如: 台北市)")
    section_name: str = Field(..., description="行政區名稱 (如: 松山區)")
    street: CleanStr = Field(None, description="街道名稱 (如: 三民路)")
    address: CleanStr = Field(None, description="地址概況描述")
    external_community_id: CleanStr = Field(None, description="外部平台所屬社區代號 (如 591 社區 ID: '5855864')")
    community_name: CleanStr = Field(None, description="所屬社區名稱")
    has_parking: bool = Field(default=False, description="是否含車位")
    cover_image_url: CleanStr = Field(None, description="封面照片網址")


class NormalizedSalePropertyDetail(BaseModel):
    """跨平台統一中古屋物理實體完整規格 (含深層產權面積拆解與完整規格)"""

    provider_id: str = Field(..., description="來源平台識別代碼 (如: '591')")
    external_house_id: str = Field(..., description="來源物件唯一刊登代號")
    title: str = Field(..., description="物件刊登標題")
    price_wan: int = Field(..., ge=0, description="總價純整數 (單位: 萬元)")
    unit_price_wan: Optional[float] = Field(None, ge=0.0, description="每坪單價浮點數 (單位: 萬元/坪)")
    total_area_pin: float = Field(..., ge=0.0, description="權狀登記總坪數浮點數 (單位: 坪)")

    # 產權面積純浮點數拆解 (單位: 坪)
    main_area_pin: Optional[float] = Field(None, ge=0.0, description="主建物坪數")
    auxiliary_area_pin: Optional[float] = Field(None, ge=0.0, description="附屬建物坪數")
    common_area_pin: Optional[float] = Field(None, ge=0.0, description="共有部分/公設坪數")
    land_area_pin: Optional[float] = Field(None, ge=0.0, description="土地持份坪數")
    parking_area_pin: Optional[float] = Field(None, ge=0.0, description="車位持份坪數")

    # 建築物理規格 (純數值)
    floor_current: Optional[int] = Field(None, description="所在樓層純整數")
    floor_total: Optional[int] = Field(None, description="總樓層數純整數")
    rooms: Optional[int] = Field(None, ge=0, description="房數純整數")
    living_rooms: Optional[int] = Field(None, ge=0, description="廳數純整數")
    bathrooms: Optional[int] = Field(None, ge=0, description="衛數純整數")
    balconies: Optional[int] = Field(None, ge=0, description="陽台數純整數")
    building_age_years: Optional[float] = Field(None, ge=0.0, description="完工屋齡浮點數 (年)")
    public_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="公設比百分比浮點數 (例如: 30.0 代表 30%)")
    management_fee_monthly: Optional[int] = Field(None, ge=0, description="每月管理費純整數 (例如: 4200)")
    has_lease: Optional[bool] = Field(None, description="是否帶租約")

    # 構造與現況描述
    building_type: CleanStr = Field(None, description="建物類型 (如: 住宅)")
    building_structure: CleanStr = Field(None, description="建築構造 (如: 電梯大樓、公寓)")
    is_whole_building: bool = Field(default=False, description="是否為整棟銷售 (如透天、整棟別墅)")
    orientation: CleanStr = Field(None, description="主要朝向 (如: 坐南朝北)")
    purpose: CleanStr = Field(None, description="法定主要用途 (如: 住家用)")
    current_state: CleanStr = Field(None, description="使用現況 (如: 住宅)")
    parking_desc: CleanStr = Field(None, description="車位型態說明")

    # 地理位置與結構化資訊
    region_name: CleanStr = Field(None, description="縣市名稱")
    section_name: CleanStr = Field(None, description="行政區名稱")
    street: CleanStr = Field(None, description="路街名稱")
    address: CleanStr = Field(None, description="完整地址描述")
    coordinates: Optional[GeoPoint] = Field(None, description="經緯度座標")
    external_community_id: CleanStr = Field(None, description="外部平台所屬社區代號 (如 591 社區 ID: '5855864')")
    community_name: CleanStr = Field(None, description="社區名稱")
    cover_image_url: CleanStr = Field(None, description="封面照片網址")


class SaleHouseSearchQuery(BaseSearchQuery):
    """跨平台統一中古屋檢索條件規範"""

    min_price_wan: Optional[int] = Field(None, ge=0, description="最低總價 (萬元)")
    max_price_wan: Optional[int] = Field(None, ge=0, description="最高總價 (萬元)")
    min_age_years: Optional[float] = Field(None, ge=0.0, description="最小屋齡 (年)")
    max_age_years: Optional[float] = Field(None, ge=0.0, description="最大屋齡 (年)")
    sort_order: Optional[str] = Field(default=None, description="排序選項")
