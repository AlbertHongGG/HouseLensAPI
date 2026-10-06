"""HouseLensAPI - API 診斷應用案例與持久化儲存 (Diagnostics Use Case & Writer)

協調整合各 Provider 探針套件執行、非同步排程延遲、全流量封包捕捉與 .tmp 目錄 JSON 落盤。
嚴禁任何裝飾性符號 (Emoji)。
"""

import asyncio
import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional
import httpx

from src.core.interfaces.diagnostics import IDiagnosticArtifactWriter, IProbeEndpoint
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.registry import ProviderRegistry, registry as default_registry
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    DiagnosticRunSummary,
    DiagnosticStatus,
    ProbeExecutionContext,
)

logger = logging.getLogger(__name__)


class JsonArtifactWriter(IDiagnosticArtifactWriter):
    """JSON 格式診斷報告落地寫入器

    將請求、回應與元數據持久化至專案根目錄下之 .tmp/api_diagnostics 資料夾。
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            # 專案根目錄 .tmp/api_diagnostics
            self.base_dir = Path.cwd() / ".tmp" / "api_diagnostics"
        else:
            self.base_dir = Path(base_dir)

    def create_run_directory(self, provider_id: str, timestamp_str: str) -> Path:
        """建立當次執行的儲存目錄 (轉換冒號以符合跨平台與 Windows 檔名規則)"""
        safe_timestamp = timestamp_str.replace(":", "-").replace("+", "_").replace(".", "_")
        target_dir = self.base_dir / provider_id / safe_timestamp
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def write_artifact(self, target_dir: Path, artifact: DiagnosticArtifact) -> Path:
        """寫入單一端點測試 JSON 記錄檔"""
        endpoint_id = artifact.metadata.endpoint_id
        target_file = target_dir / f"{endpoint_id}.json"
        content = json.dumps(artifact.model_dump(), indent=2, ensure_ascii=False)
        target_file.write_text(content, encoding="utf-8")
        return target_file

    def write_summary(self, target_dir: Path, summary: DiagnosticRunSummary) -> Path:
        """寫入批次執行總結報告 summary.json"""
        target_file = target_dir / "summary.json"
        content = json.dumps(summary.model_dump(), indent=2, ensure_ascii=False)
        target_file.write_text(content, encoding="utf-8")
        return target_file

    def write_single_probe_artifact(
        self,
        provider_id: str,
        artifact: DiagnosticArtifact,
        custom_file_path: Optional[Path] = None,
    ) -> Path:
        """寫入單一端點測試 JSON 記錄檔至指定路徑或預設 single_probes 目錄"""
        content = json.dumps(artifact.model_dump(), indent=2, ensure_ascii=False)
        if custom_file_path is not None:
            target_path = Path(custom_file_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return target_path

        target_dir = self.base_dir / provider_id / "single_probes"
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_time = (
            artifact.metadata.timestamp.replace(":", "-")
            .replace("+", "_")
            .replace(".", "_")
        )
        endpoint_id = artifact.metadata.endpoint_id
        target_file = target_dir / f"{endpoint_id}_{safe_time}.json"
        target_file.write_text(content, encoding="utf-8")
        return target_file


class DiagnosticsUseCase:
    """API 診斷與全端點健康檢測業務案例"""

    def __init__(
        self,
        provider_registry: Optional[ProviderRegistry] = None,
        writer: Optional[IDiagnosticArtifactWriter] = None,
    ):
        self._registry = provider_registry or default_registry
        self._writer = writer or JsonArtifactWriter()

    async def run(
        self,
        provider_id: Optional[str] = None,
        domain: Optional[DiagnosticDomain] = None,
        delay_seconds: float = 1.0,
        on_progress: Optional[Callable[[IProbeEndpoint, DiagnosticArtifact, int, int], None]] = None,
    ) -> List[DiagnosticRunSummary]:
        """相容執行套件檢測"""
        return await self.run_suite(
            provider_id=provider_id,
            domain=domain,
            delay_seconds=delay_seconds,
            on_progress=on_progress,
        )

    async def run_suite(
        self,
        provider_id: Optional[str] = None,
        domain: Optional[DiagnosticDomain] = None,
        delay_seconds: float = 1.0,
        on_progress: Optional[Callable[[IProbeEndpoint, DiagnosticArtifact, int, int], None]] = None,
    ) -> List[DiagnosticRunSummary]:
        """依序執行目標 Provider 之全部探針套件並錄製流量

        Args:
            provider_id: 指定來源代碼 (例如 '591')，若為 None 則依序測試全部註冊來源
            domain: 篩選特定業務領域 (例如 DiagnosticDomain.SALE)
            delay_seconds: 端點調用間冷卻秒數 (防止觸發頻率限制)
            on_progress: 單一端點完成時之即時回呼函式 (probe, artifact, current_index, total_count)

        Returns:
            List[DiagnosticRunSummary]: 各來源之批次診斷總結報告
        """
        target_providers: List[IHouseSourceProvider] = []
        if provider_id:
            provider = self._registry.get(provider_id)
            if not provider:
                raise ValueError(
                    f"未找到已註冊的來源提供者: '{provider_id}'，可用: {self._registry.list_available()}"
                )
            target_providers.append(provider)
        else:
            all_providers = self._registry.get_all()
            if not all_providers:
                raise ValueError("系統中無任何已註冊之來源提供者")
            target_providers.extend(all_providers)

        summaries: List[DiagnosticRunSummary] = []

        for provider in target_providers:
            summary = await self._run_single_provider(
                provider=provider,
                domain=domain,
                delay_seconds=delay_seconds,
                on_progress=on_progress,
            )
            summaries.append(summary)

        return summaries

    async def run_endpoint(
        self,
        provider_id: str,
        endpoint_id: str,
        target_id: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        custom_file_path: Optional[Path] = None,
    ) -> tuple[DiagnosticArtifact, Path]:
        """執行特定 Provider 的單一 API 端點功能性測試並錄製流量快照

        Args:
            provider_id: 目標來源外掛代碼 (例如 '591')
            endpoint_id: 端點代碼 (例如 'sale_detail')
            target_id: 自訂目標物件/實體 ID (例如 'S20846137')
            extra_params: 自訂覆蓋或追加之 Query 參數
            extra_headers: 自訂覆蓋或追加之 HTTP 標頭
            custom_file_path: 自訂落盤檔案路徑

        Returns:
            tuple[DiagnosticArtifact, Path]: 診斷快照實體與落盤檔案路徑
        """
        provider = self._registry.get(provider_id)
        if not provider:
            raise ValueError(
                f"未找到已註冊的來源提供者: '{provider_id}'，可用: {self._registry.list_available()}"
            )

        probe = provider.diagnostics.get_probe(endpoint_id)
        if not probe:
            available_ids = [p.endpoint_id for p in provider.diagnostics.get_probes()]
            raise ValueError(
                f"來源 '{provider_id}' 未包含端點 '{endpoint_id}'。可用端點代碼: {available_ids}"
            )

        exec_context = ProbeExecutionContext(
            target_id=target_id,
            extra_params=extra_params or {},
            extra_headers=extra_headers or {},
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            artifact = await probe.execute(client, context=exec_context)

        saved_path = self._writer.write_single_probe_artifact(
            provider_id=provider.provider_id,
            artifact=artifact,
            custom_file_path=custom_file_path,
        )
        return artifact, saved_path

    def list_probes(
        self,
        provider_id: Optional[str] = None,
        domain: Optional[DiagnosticDomain] = None,
    ) -> List[tuple[IHouseSourceProvider, IProbeEndpoint]]:
        """查詢已註冊之來源與探針規格清單

        Args:
            provider_id: 指定來源代碼，若為 None 則列出所有來源
            domain: 篩選業務領域

        Returns:
            List[tuple[IHouseSourceProvider, IProbeEndpoint]]: 來源與探針元組清單
        """
        target_providers: List[IHouseSourceProvider] = []
        if provider_id:
            provider = self._registry.get(provider_id)
            if not provider:
                raise ValueError(
                    f"未找到已註冊的來源提供者: '{provider_id}'，可用: {self._registry.list_available()}"
                )
            target_providers.append(provider)
        else:
            target_providers.extend(self._registry.get_all())

        results: List[tuple[IHouseSourceProvider, IProbeEndpoint]] = []
        for p in target_providers:
            probes = p.diagnostics.get_probes(domain=domain)
            for probe in probes:
                results.append((p, probe))

        return results

    async def _run_single_provider(
        self,
        provider: IHouseSourceProvider,
        domain: Optional[DiagnosticDomain],
        delay_seconds: float,
        on_progress: Optional[Callable[[IProbeEndpoint, DiagnosticArtifact, int, int], None]],
    ) -> DiagnosticRunSummary:
        """執行單一 Provider 的診斷探針測試流程"""
        diag_suite = provider.diagnostics
        probes = diag_suite.get_probes(domain=domain)

        now_str = datetime.datetime.now().astimezone().isoformat()
        run_id = f"{provider.provider_id}_{now_str}"
        run_dir = self._writer.create_run_directory(provider.provider_id, now_str)

        total_probes = len(probes)
        successful = 0
        failed = 0
        start_time = time.perf_counter()
        artifacts_paths: List[str] = []
        endpoints_meta = []

        # 使用專用連線客戶端循序發送
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            for idx, probe in enumerate(probes):
                try:
                    artifact = await probe.execute(client, context=None)
                except Exception as exc:
                    logger.error("探針執行未預期異常: %s - %s", probe.endpoint_id, exc)
                    from src.domain.diagnostics import (
                        DiagnosticMetadata,
                        DiagnosticRequestSnapshot,
                    )

                    metadata = DiagnosticMetadata(
                        provider_id=provider.provider_id,
                        provider_name=provider.provider_name,
                        endpoint_id=probe.endpoint_id,
                        domain=probe.domain.value,
                        name=probe.name,
                        description=probe.description,
                        status=DiagnosticStatus.PARSING_ERROR,
                        status_code=None,
                        latency_ms=0.0,
                        timestamp=datetime.datetime.now().astimezone().isoformat(),
                        error_message=f"探針異常崩潰: {type(exc).__name__} - {str(exc)}",
                    )
                    request_snapshot = DiagnosticRequestSnapshot(
                        method="UNKNOWN",
                        url="UNKNOWN",
                        headers={},
                        params={},
                        body=None,
                    )
                    artifact = DiagnosticArtifact(
                        metadata=metadata,
                        request=request_snapshot,
                        response=None,
                    )

                # 落盤單一端點測試結果
                saved_path = self._writer.write_artifact(run_dir, artifact)
                artifacts_paths.append(str(saved_path))
                endpoints_meta.append(artifact.metadata)

                if artifact.metadata.status == DiagnosticStatus.SUCCESS:
                    successful += 1
                else:
                    failed += 1

                if on_progress:
                    on_progress(probe, artifact, idx + 1, total_probes)

                # 冷卻步調控制 (最後一個端點除外)
                if delay_seconds > 0 and idx < total_probes - 1:
                    await asyncio.sleep(delay_seconds)

        total_duration = round((time.perf_counter() - start_time) * 1000, 2)

        summary = DiagnosticRunSummary(
            run_id=run_id,
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            timestamp=now_str,
            total_endpoints=total_probes,
            successful_endpoints=successful,
            failed_endpoints=failed,
            total_duration_ms=total_duration,
            artifacts=artifacts_paths,
            endpoints=endpoints_meta,
        )

        # 落盤批次總結報告
        self._writer.write_summary(run_dir, summary)
        return summary

