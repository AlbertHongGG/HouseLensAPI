"""HouseLensAPI - 社區領域模型 (Community Domain Models)

定義社區清單摘要 (CommunitySummary)、社區極致詳情 (CommunityDetail) 與檢索條件 (CommunitySearchQuery)。
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.domain.common import GeoPoint


class CommunitySummary(BaseModel):
    """社區清單摘要物件 (由多元搜尋與瀏覽端點產出)"""
    community_id: str = Field(..., description="社區唯一識別碼 (字串)")
    hid: Optional[int] = Field(None, description="社區/建案關聯 HID")
    community_name: str = Field(..., description="社區名稱")
    build_purpose_simple: Optional[str] = Field(None, description="建物用途分類 (例如: 住宅)")
    building_type_str: Optional[str] = Field(None, description="建物型態 (例如: 新成屋、預售屋、電梯大樓)")
    region_name: str = Field(..., description="縣市名稱 (例如: 台北市)")
    section_name: str = Field(..., description="行政區名稱 (例如: 松山區)")
    simple_address: Optional[str] = Field(None, description="簡短街道地址")
    full_address: str = Field(..., description="完整地理地址")
    coordinates: Optional[GeoPoint] = Field(None, description="社區經緯度座標")
    avg_unit_price: Optional[float] = Field(None, description="社區均價 (萬元/坪)")
    unit_price_unit: Optional[str] = Field(None, description="均價單位 (例如: 萬/坪)")
    living_circle_name: Optional[str] = Field(None, description="所屬生活圈/商圈名稱")
    nearest_station: Optional[str] = Field(None, description="鄰近捷運/鐵路站點名稱")
    cover_image_url: Optional[str] = Field(None, description="社區封面圖片網址")


class CommunityDetail(BaseModel):
    """社區完整詳情物件 (涵蓋規格、建商營造團隊、公設與特色)"""
    community_id: str = Field(..., description="社區唯一代號")
    community_name: str = Field(..., description="社區名稱")
    build_type_str: Optional[str] = Field(None, description="建物型態")
    purpose_str: Optional[str] = Field(None, description="法定主要用途")
    transport: Optional[str] = Field(None, description="大眾運輸交通說明")
    address: str = Field(..., description="社區完整地址")
    region_name: str = Field(..., description="縣市名稱")
    section_name: str = Field(..., description="行政區名稱")
    shopping_district: Optional[str] = Field(None, description="生活圈商圈名稱")

    # 建築硬體與規劃規格 (build_info)
    park_rate: Optional[str] = Field(None, description="車位配比 (例如: 1:1.07)")
    direction_rule: Optional[str] = Field(None, description="基地座向規則 (例如: 朝北、朝南)")
    build_intro: Optional[str] = Field(None, description="建案特色、設備與工法說明")
    landscape_name: Optional[str] = Field(None, description="景觀設計公司")
    postulate_name: Optional[str] = Field(None, description="公設設計公司")
    park_type_str: Optional[str] = Field(None, description="車位型態 (例如: 平面式)")
    age: Optional[str] = Field(None, description="完工屋齡")
    total_households: Optional[str] = Field(None, description="總戶數規劃")
    floor_plan: Optional[str] = Field(None, description="地上與地下樓層規劃 (例如: 地上24層,地下4層)")
    structure: Optional[str] = Field(None, description="建築結構工法 (例如: SRC造)")
    base_area_ping: Optional[str] = Field(None, description="基地面積 (坪)")
    public_ratio: Optional[str] = Field(None, description="公設比率")
    parking_count: Optional[str] = Field(None, description="規劃車位總數")
    facilities: List[str] = Field(default_factory=list, description="公共設施項目清單")
    developer_company: Optional[str] = Field(None, description="投資興建公司")
    builder_company: Optional[str] = Field(None, description="營造公司")
    architect_company: Optional[str] = Field(None, description="建築設計事務所")
    management_fee: Optional[str] = Field(None, description="管理費單價 (例如: 100元/坪/月)")


class CommunitySearchQuery(BaseModel):
    """社區檢索條件參數"""
    region_id: Optional[int] = Field(None, description="縣市代碼 (1: 台北市...)")
    section_id: Optional[int] = Field(None, description="行政區代碼")
    keyword: Optional[str] = Field(None, description="搜尋關鍵字 (社區名稱/地址/生活圈)")
    age_ranges: List[str] = Field(default_factory=list, description="屋齡區間代碼清單 (如: ['0_5', '5_10'])")
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    is_sale: Optional[int] = Field(default=0, description="是否僅篩選在售物件")
    post_type: str = Field(default="8,2", description="刊登型態標籤")
