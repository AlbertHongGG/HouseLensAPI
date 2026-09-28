"""HouseLensAPI - 新建案領域模型 (New House Domain Models)

定義新建案清單摘要 (NewHouseSummary)、規劃房型項目 (NewHouseLayoutItem)、建案完整詳情 (NewHouseDetail) 與檢索條件 (NewHouseSearchQuery)。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NewHouseLayoutItem(BaseModel):
    """建案標準規劃房型與坪數項目 (對應 layout_v2)"""
    room: str = Field(..., description="房型規格描述 (例如: 一房、二房、三房)")
    area: str = Field(..., description="對應坪數區間 (例如: 14~17、18~26、30~41)")


class NewHouseSummary(BaseModel):
    """新建案清單摘要物件 (由新建案檢索列表產出)"""
    source_hid: int = Field(..., description="建案唯一識別碼 (HID)")
    project_name: str = Field(..., description="建案名稱")
    project_status: str = Field(..., description="建案期程狀態 (預售屋/新成屋)")
    region_name: str = Field(..., description="縣市名稱 (例如: 台北市)")
    section_name: str = Field(..., description="行政區名稱 (例如: 萬華區)")
    address: str = Field(..., description="基地或接待地址")
    price: str = Field(..., description="單價區間字串 (例如: 79~90)")
    area: str = Field(..., description="坪數區間字串 (例如: 28~41坪)")
    room_layout_summary: Optional[str] = Field(None, description="房型概況 (例如: 2~4房)")
    developer: Optional[str] = Field(None, description="投資興建公司")
    cover_image_url: Optional[str] = Field(None, description="建案封面照片網址")


class NewHouseDetail(BaseModel):
    """新建案完整詳情物件 (全量落實結構化 layout_v2 與完整建築規劃)"""
    hid: int = Field(..., description="建案 HID")
    project_name: str = Field(..., description="建案名稱")
    build_type: str = Field(..., description="建案狀態型態 (預售屋/新成屋)")
    region: str = Field(..., description="縣市名稱 (例如: 台北市)")
    section: str = Field(..., description="行政區名稱 (例如: 萬華區)")
    address: str = Field(..., description="基地位置地址")
    manage_cost: Optional[str] = Field(None, description="管理費標準 (例如: 150 元/坪/月)")
    structural_engine: Optional[str] = Field(None, description="建築結構工法 (例如: SRC鋼骨鋼筋混凝土結構)")
    park_planning: Optional[str] = Field(None, description="車位規劃描述 (例如: 平面式111個、機械式41個)")
    direction_rule: Optional[str] = Field(None, description="座向規劃 (例如: 朝西北)")
    build_intro: Optional[str] = None
    park_ratio: Optional[str] = Field(None, description="車位配比 (例如: 1:0.46)")
    layout_v2: List[NewHouseLayoutItem] = Field(default_factory=list, description="結構化房型坪數規劃列表")
    unit_price_str: Optional[str] = Field(None, description="開價單價區間 (例如: 100~110 萬/坪)")
    parking_price_str: Optional[str] = Field(None, description="車位價格區間 (例如: 360~420萬)")
    base_area_ping: Optional[float] = Field(None, description="基地總面積 (坪)")
    public_ratio: Optional[str] = Field(None, description="公設比率 (例如: 34%)")
    total_households: Optional[str] = Field(None, description="規劃總戶數 (例如: 290戶)")
    developer_company: Optional[str] = Field(None, description="投資建設公司")
    builder_company: Optional[str] = Field(None, description="營造公司")
    architect_company: Optional[str] = Field(None, description="建築設計事務所")
    reception_address: Optional[str] = Field(None, description="接待會館地址")
    community_id_ref: Optional[int] = Field(None, description="關聯之社區 ID")


class NewHouseSearchQuery(BaseModel):
    """新建案檢索條件參數"""
    region_id: Optional[int] = Field(None, description="縣市代碼")
    keywords: Optional[str] = Field(None, description="建案關鍵字")
    build_status: Optional[str] = Field(default="1,2", description="建案狀態 (1: 預售屋, 2: 新成屋)")
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
