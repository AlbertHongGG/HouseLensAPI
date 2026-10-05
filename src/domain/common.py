"""HouseLensAPI - 通用領域基礎型別 (Common Domain Models)

定義座標系統、結構化地址與標準泛型分頁查詢/結果模型。
"""

from typing import Annotated, Any, Dict, Generic, List, Optional, Self, TypeVar, Union
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

T = TypeVar("T")


def sanitize_optional_str(val: Any) -> Optional[str]:
    """領域模型不變量純化器：強制清除前後空白，並將空字串、空白與常見無效佔位符統一純化為 None。

    支援過濾: "", "   ", "-", "--", "---", "無", "暫無", "未提供", "待定", "價格待定", "None", "null"
    """
    if val is None:
        return None

    s = str(val).strip()
    if not s:
        return None

    invalid_placeholders = {
        "-",
        "--",
        "---",
        "無",
        "暫無",
        "暫無資料",
        "暫無數據",
        "暂无",
        "暂无数据",
        "未提供",
        "待定",
        "價格待定",
        "不詳",
        "未知",
        "None",
        "none",
        "null",
        "NULL",
    }
    if s in invalid_placeholders:
        return None

    return s


# 核心領域強型別：自衛性非空文字型別 (自動防禦空字串與佔位符)
CleanStr = Annotated[Optional[str], BeforeValidator(sanitize_optional_str)]


class GeoPoint(BaseModel):
    """標準 WGS-84 地理經緯度座標"""
    lat: float = Field(..., description="緯度 (Latitude)")
    lng: float = Field(..., description="經度 (Longitude)")



class StructuredAddress(BaseModel):
    """標準結構化地理地址表示"""
    region: str = Field(..., description="一級行政區/縣市 (例如: 台北市)")
    section: Optional[str] = Field(None, description="二級行政區/鄉鎮市區 (例如: 松山區)")
    street: Optional[str] = Field(None, description="路街名 (例如: 三民路)")
    lane: Optional[str] = Field(None, description="巷 (例如: 80巷)")
    alley: Optional[str] = Field(None, description="弄 (例如: 15弄)")
    number: Optional[str] = Field(None, description="門牌號碼 (例如: 25號)")
    full_address: str = Field(..., description="完整單一行地址描述")
    coordinates: Optional[GeoPoint] = Field(None, description="經緯度座標")


class PageQuery(BaseModel):
    """通用分頁查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼，由 1 開始")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")


class BaseSearchQuery(PageQuery):
    """跨領域搜尋檢索抽象基底規格 (提供自省抽取與安全欄位過濾能力)"""

    model_config = ConfigDict(extra="ignore")

    region_id: Optional[int] = Field(None, description="標準縣市代碼")
    section_id: Optional[int] = Field(None, description="標準行政區代碼")
    keywords: Optional[str] = Field(None, description="搜尋關鍵字")

    @classmethod
    def from_options(cls, options: Union[BaseModel, Dict[str, Any], Any]) -> Self:
        """從統一條件物件、字典或模型中自省提取本模型宣告之有效欄位，未宣告欄位原生忽略"""
        if isinstance(options, BaseModel):
            data = options.model_dump(exclude_none=True)
        elif isinstance(options, dict):
            data = {k: v for k, v in options.items() if v is not None}
        else:
            data = {k: v for k, v in vars(options).items() if v is not None}
        return cls.model_validate(data)


class PageResult(BaseModel, Generic[T]):
    """通用強型別泛型分頁結果容器"""
    items: List[T] = Field(default_factory=list, description="當頁資料列表")
    total_records: int = Field(default=0, ge=0, description="總筆數")
    page: int = Field(default=1, ge=1, description="當前頁碼")
    page_size: int = Field(default=20, ge=1, description="每頁筆數")
    has_next: bool = Field(default=False, description="是否還有下一頁")

    @classmethod
    def create(cls, items: List[T], total_records: int, page: int, page_size: int) -> "PageResult[T]":
        """工廠方法自動推算 has_next"""
        has_next = (page * page_size) < total_records
        return cls(
            items=items,
            total_records=total_records,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )
