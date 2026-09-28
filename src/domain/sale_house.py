"""HouseLensAPI - 中古屋領域模型 (Sale House Domain Models)

定義跨平台統一之中古屋清單摘要 (SaleHouseSummary)、詳情規格 (SaleHouseDetail) 與檢索條件 (SaleHouseSearchQuery)。
全量遵循無冗餘、無平台特化代碼、單一事實來源之架構原則。
"""

from typing import Optional
from pydantic import BaseModel, Field


class SaleHouseSummary(BaseModel):
    """跨平台統一中古屋清單摘要物件 (由搜尋與條件瀏覽產出)"""
    house_id: str = Field(..., description="來源物件唯一刊登代號 (例如: S20604856)")
    title: str = Field(..., description="物件刊登標題")
    price: str = Field(..., description="刊登總價描述 (例如: 5,258萬元)")
    unit_price: Optional[str] = Field(None, description="每坪單價 (例如: 132.2萬/坪)")
    total_area: Optional[float] = Field(None, description="權狀登記總坪數數值 (例如: 46.3)")
    layout: Optional[str] = Field(None, description="格局描述 (例如: 3房2廳)")
    building_type: Optional[str] = Field(None, description="建物類型 (例如: 住宅)")
    region: str = Field(..., description="縣市名稱 (例如: 台北市)")
    section: str = Field(..., description="行政區名稱 (例如: 松山區)")
    street: Optional[str] = Field(None, description="街道名稱 (例如: 三民路)")
    address: Optional[str] = Field(None, description="地址概況描述")
    community_id: Optional[str] = Field(None, description="所屬社區 ID")
    community_name: Optional[str] = Field(None, description="所屬社區名稱")
    floor: Optional[str] = Field(None, description="所在樓層 (例如: 2)")
    total_floor: Optional[str] = Field(None, description="總樓層數 (例如: 24)")
    age: Optional[str] = Field(None, description="屋齡文字描述 (例如: 1年)")
    building_age: Optional[float] = Field(None, description="屋齡數值 (例如: 1.0)")
    has_parking: bool = Field(default=False, description="是否含車位")
    cover_image_url: Optional[str] = Field(None, description="封面照片網址")


class SaleHouseDetail(BaseModel):
    """跨平台統一中古屋標準詳情物件 (純淨無冗餘領域契約)"""
    house_id: str = Field(..., description="房屋唯一代號 (例如: 20604856)")
    title: str = Field(..., description="物件刊登標題")
    price: int = Field(..., description="總價萬元純整數 (例如: 5258)")
    unit_price: Optional[str] = Field(None, description="每坪單價描述 (例如: 132.2萬/坪)")
    layout: Optional[str] = Field(None, description="完整格局描述 (例如: 3房2廳2衛)")
    total_area: Optional[float] = Field(None, description="權狀登記總坪數浮點數 (例如: 46.29)")
    building_type: Optional[str] = Field(None, description="建物類型 (例如: 住宅)")
    building_structure: Optional[str] = Field(None, description="建築構造型態 (例如: 電梯大樓、公寓)")

    # 核心建築規格
    floor: Optional[str] = Field(None, description="所在與總樓層區間 (例如: 2F/24F)")
    age: Optional[str] = Field(None, description="完工屋齡文字描述 (例如: 1年、33年)")
    building_age: Optional[float] = Field(None, description="完工屋齡數值 (例如: 1.0, 33.0)")
    orientation: Optional[str] = Field(None, description="主要朝向 (例如: 坐南朝北)")
    management_fee: Optional[str] = Field(None, description="管理費 (例如: 4200元/月、無)")
    public_ratio: Optional[str] = Field(None, description="公設比率 (例如: 30%)")
    has_lease: Optional[str] = Field(None, description="是否帶租約 (例如: 否、是)")
    balcony: Optional[str] = Field(None, description="陽台數 (例如: 1個)")
    purpose: Optional[str] = Field(None, description="法定主要用途 (例如: 住家用、依使用執照)")
    current_state: Optional[str] = Field(None, description="使用現況 (例如: 住宅)")
    parking_desc: Optional[str] = Field(None, description="車位型態與說明 (例如: 平面式，已含售金內)")

    # 產權坪數明細 (單一事實來源)
    main_building_area: Optional[str] = Field(None, description="主建物坪數 (例如: 23.10坪)")
    auxiliary_area: Optional[str] = Field(None, description="附屬建物坪數 (例如: 2.78坪)")
    common_area: Optional[str] = Field(None, description="共有部分坪數 (例如: 11.17坪)")
    land_area: Optional[str] = Field(None, description="土地持份坪數 (例如: 5.06坪)")
    parking_area: Optional[str] = Field(None, description="車位坪數 (例如: 9.24坪)")

    # 地理位置與座標
    region: Optional[str] = Field(None, description="縣市名稱")
    section: Optional[str] = Field(None, description="行政區名稱")
    street: Optional[str] = Field(None, description="路街名稱")
    address: Optional[str] = Field(None, description="完整結構化地址")
    lat: Optional[float] = Field(None, description="緯度浮點數")
    lng: Optional[float] = Field(None, description="經度浮點數")


class SaleHouseSearchQuery(BaseModel):
    """中古屋檢索條件參數"""
    region_id: Optional[int] = Field(None, description="縣市代碼")
    section_id: Optional[int] = Field(None, description="行政區代碼")
    keywords: Optional[str] = Field(None, description="搜尋關鍵字 (標題/社區/路名)")
    page: int = Field(default=1, ge=1, description="頁碼")
    kind: Optional[int] = Field(default=0, description="物件型態代碼 (0: 全部)")
    min_price: Optional[int] = Field(None, description="最低總價 (萬元)")
    max_price: Optional[int] = Field(None, description="最高總價 (萬元)")
    min_age: Optional[int] = Field(None, ge=0, description="最小屋齡 (年)")
    max_age: Optional[int] = Field(None, ge=0, description="最大屋齡 (年)")
    sort_order: Optional[str] = Field(default="90", description="排序模式")
