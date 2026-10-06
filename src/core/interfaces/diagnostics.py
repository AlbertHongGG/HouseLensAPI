"""HouseLensAPI - API 診斷探針抽象介面 (Diagnostics Interfaces)

定義單一端點測試規格 (IProbeEndpoint) 與來源外掛診斷聚合介面 (IProviderDiagnostics)。
完全解耦核心層與各第三方平台 API 實作細節。
嚴禁任何裝飾性符號 (Emoji)。
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import httpx

from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    ProbeExecutionContext,
)


class IProbeEndpoint(ABC):
    """單一 API 端點之診斷探針規格合約"""

    @property
    @abstractmethod
    def endpoint_id(self) -> str:
        """端點唯一標識代碼，例如 'community_list', 'sale_detail'"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """端點顯示名稱"""
        pass

    @property
    @abstractmethod
    def domain(self) -> DiagnosticDomain:
        """所屬業務領域"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """端點測試用途描述"""
        pass

    @property
    def requires_target_id(self) -> bool:
        """此端點是否為詳情類型且支援指定目標 ID (預設 False)"""
        return False

    @property
    def default_target_id(self) -> Optional[str]:
        """若未提供目標 ID 時之預設測試種子 ID (預設 None)"""
        return None

    @abstractmethod
    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        """執行端點探針測試並回傳完整流量快照與判定結果"""
        pass


class IProviderDiagnostics(ABC):
    """來源提供者診斷套件聚合介面合約"""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """所屬來源代碼"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """所屬來源名稱"""
        pass

    @abstractmethod
    def get_probes(self, domain: Optional[DiagnosticDomain] = None) -> List[IProbeEndpoint]:
        """取得該來源註冊之所有探針，可依領域進行篩選"""
        pass

    @abstractmethod
    def get_probe(self, endpoint_id: str) -> Optional[IProbeEndpoint]:
        """依端點唯一代碼檢索特定探針實例"""
        pass


class IDiagnosticArtifactWriter(ABC):
    """診斷報告落地儲存合約"""

    @abstractmethod
    def create_run_directory(self, provider_id: str, timestamp_str: str) -> Any:
        """建立當次執行的儲存目錄"""
        pass

    @abstractmethod
    def write_artifact(self, target_dir: Any, artifact: DiagnosticArtifact) -> Any:
        """寫入單一端點測試 JSON 記錄檔"""
        pass

    @abstractmethod
    def write_summary(self, target_dir: Any, summary: Any) -> Any:
        """寫入批次執行總結報告 summary.json"""
        pass

    @abstractmethod
    def write_single_probe_artifact(
        self,
        provider_id: str,
        artifact: DiagnosticArtifact,
        custom_file_path: Optional[Any] = None,
    ) -> Any:
        """寫入單一端點測試 JSON 記錄檔至指定路徑或預設 single_probes 目錄"""
        pass

