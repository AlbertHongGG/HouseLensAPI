"""HouseLensAPI - API 診斷領域數據模型 (Diagnostic Domain Models)

定義端點健康檢測之全流量快照、診斷元數據與執行摘要模型。
嚴禁任何裝飾性符號 (Emoji)。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiagnosticStatus(str, Enum):
    """端點診斷結果狀態"""
    SUCCESS = "SUCCESS"
    HTTP_ERROR = "HTTP_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    PARSING_ERROR = "PARSING_ERROR"


class DiagnosticDomain(str, Enum):
    """端點所屬業務領域"""
    COMMUNITY = "community"
    SALE = "sale"
    NEW_HOUSE = "newhouse"
    SYSTEM = "system"


class DiagnosticMetadata(BaseModel):
    """API 診斷探針執行元數據"""
    provider_id: str = Field(..., description="來源提供者唯一代碼 (如 591)")
    provider_name: str = Field(..., description="來源提供者顯示名稱")
    endpoint_id: str = Field(..., description="端點唯一標識 (如 sale_list)")
    domain: str = Field(..., description="業務領域 (community, sale, newhouse, system)")
    name: str = Field(..., description="端點名稱")
    description: str = Field(..., description="端點測試功能描述")
    status: DiagnosticStatus = Field(..., description="診斷執行狀態")
    status_code: Optional[int] = Field(None, description="HTTP 狀態碼")
    latency_ms: float = Field(0.0, description="請求耗時 (毫秒)")
    timestamp: str = Field(..., description="診斷執行時間戳 (ISO 8601)")
    error_message: Optional[str] = Field(None, description="錯誤訊息或例外堆疊")


class DiagnosticRequestSnapshot(BaseModel):
    """送出之完整 HTTP 請求快照"""
    method: str = Field(..., description="HTTP 動詞 (GET, POST 等)")
    url: str = Field(..., description="完整連線 URL (包含 query string)")
    headers: Dict[str, str] = Field(default_factory=dict, description="請求標頭 (已脫敏)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Query 參數字典")
    body: Optional[Any] = Field(None, description="請求主體資料")


class DiagnosticResponseSnapshot(BaseModel):
    """接收之完整 HTTP 回應快照"""
    status_code: int = Field(..., description="HTTP 回應狀態碼")
    latency_ms: float = Field(..., description="伺服器回應耗時 (毫秒)")
    headers: Dict[str, str] = Field(default_factory=dict, description="回應標頭")
    body: Optional[Any] = Field(None, description="回應主體 (JSON 解析物件或純文字)")


class DiagnosticArtifact(BaseModel):
    """單一 API 端點之完整診斷報告實體 (落盤至 JSON)"""
    metadata: DiagnosticMetadata = Field(..., description="診斷元數據")
    request: DiagnosticRequestSnapshot = Field(..., description="請求快照")
    response: Optional[DiagnosticResponseSnapshot] = Field(None, description="回應快照")


class DiagnosticRunSummary(BaseModel):
    """批次診斷執行總結報告"""
    run_id: str = Field(..., description="執行批次唯一標識")
    provider_id: str = Field(..., description="來源提供者代碼")
    provider_name: str = Field(..., description="來源提供者名稱")
    timestamp: str = Field(..., description="批次開始時間戳")
    total_endpoints: int = Field(0, description="總測試端點數")
    successful_endpoints: int = Field(0, description="成功端點數")
    failed_endpoints: int = Field(0, description="失敗端點數")
    total_duration_ms: float = Field(0.0, description="總執行耗時 (毫秒)")
    artifacts: List[str] = Field(default_factory=list, description="落盤檔案清單")
    endpoints: List[DiagnosticMetadata] = Field(default_factory=list, description="端點測試結果清單")
