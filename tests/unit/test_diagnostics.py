"""HouseLensAPI - API 診斷探針與流量錄製單元測試 (Unit Tests for Diagnostics)

驗證資料模型、流量錄製攔截器、脫敏機制、持久化寫入器與 591 探針套件。
嚴格遵守零裝飾性符號 (Zero Emoji) 規範。
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from src.application.diagnostics_usecase import DiagnosticsUseCase, JsonArtifactWriter
from src.core.diagnostics.recorder import (
    DiagnosticTransportRecorder,
    sanitize_headers,
)
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.registry import ProviderRegistry
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    DiagnosticMetadata,
    DiagnosticRequestSnapshot,
    DiagnosticResponseSnapshot,
    DiagnosticRunSummary,
    DiagnosticStatus,
)
from src.providers.source_591.diagnostics import (
    HealthPingProbe,
    Source591Diagnostics,
)
from src.providers.source_591.provider import Source591Provider


def test_sanitize_headers():
    """驗證敏感標頭自動脫敏"""
    raw_headers = {
        "User-Agent": "HouseLens/1.0",
        "Authorization": "Bearer secret_jwt_token_123",
        "Cookie": "session_id=abcdef; token=xyz",
        "X-Auth-Token": "top_secret_token",
        "Accept": "application/json",
    }
    sanitized = sanitize_headers(raw_headers)

    assert sanitized["User-Agent"] == "HouseLens/1.0"
    assert sanitized["Accept"] == "application/json"
    assert sanitized["Authorization"] == "***"
    assert sanitized["Cookie"] == "***"
    assert sanitized["X-Auth-Token"] == "***"


@pytest.mark.asyncio
async def test_diagnostic_recorder_success():
    """驗證 HTTP 正常回應之快照與計時錄製"""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": 1, "data": {"items": [1, 2, 3]}}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.headers = {"User-Agent": "TestClient/1.0"}
    mock_client.request.return_value = mock_response

    metadata = DiagnosticMetadata(
        provider_id="test_p",
        provider_name="Test Provider",
        endpoint_id="test_ep",
        domain="community",
        name="測試端點",
        description="測試描述",
        status=DiagnosticStatus.SUCCESS,
        status_code=None,
        latency_ms=0.0,
        timestamp="",
    )

    artifact = await DiagnosticTransportRecorder.capture(
        client=mock_client,
        metadata=metadata,
        method="GET",
        url="https://api.example.com/test",
        params={"page": 1},
        headers={"custom-header": "test-val"},
    )

    assert artifact.metadata.status == DiagnosticStatus.SUCCESS
    assert artifact.metadata.status_code == 200
    assert artifact.metadata.latency_ms >= 0.0
    assert artifact.request.method == "GET"
    assert artifact.request.url == "https://api.example.com/test"
    assert artifact.request.params == {"page": 1}
    assert artifact.response is not None
    assert artifact.response.status_code == 200
    assert artifact.response.body == {"status": 1, "data": {"items": [1, 2, 3]}}


@pytest.mark.asyncio
async def test_diagnostic_recorder_http_error():
    """驗證 HTTP 403 異常之錯誤捕獲與標記"""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"content-type": "text/html"}
    mock_response.json.side_effect = ValueError("Not JSON")
    mock_response.text = "Forbidden Access"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.headers = {}
    mock_client.request.return_value = mock_response

    metadata = DiagnosticMetadata(
        provider_id="test_p",
        provider_name="Test Provider",
        endpoint_id="test_ep",
        domain="sale",
        name="測試端點",
        description="測試描述",
        status=DiagnosticStatus.SUCCESS,
        status_code=None,
        latency_ms=0.0,
        timestamp="",
    )

    artifact = await DiagnosticTransportRecorder.capture(
        client=mock_client,
        metadata=metadata,
        method="GET",
        url="https://api.example.com/forbidden",
    )

    assert artifact.metadata.status == DiagnosticStatus.HTTP_ERROR
    assert artifact.metadata.status_code == 403
    assert "403" in (artifact.metadata.error_message or "")
    assert artifact.response is not None
    assert artifact.response.body == "Forbidden Access"


@pytest.mark.asyncio
async def test_diagnostic_recorder_timeout():
    """驗證連線逾時例外之處理與快照記錄"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.headers = {}
    mock_client.request.side_effect = httpx.ConnectTimeout("Connection timed out")

    metadata = DiagnosticMetadata(
        provider_id="test_p",
        provider_name="Test Provider",
        endpoint_id="test_ep",
        domain="newhouse",
        name="測試端點",
        description="測試描述",
        status=DiagnosticStatus.SUCCESS,
        status_code=None,
        latency_ms=0.0,
        timestamp="",
    )

    artifact = await DiagnosticTransportRecorder.capture(
        client=mock_client,
        metadata=metadata,
        method="GET",
        url="https://api.example.com/timeout",
    )

    assert artifact.metadata.status == DiagnosticStatus.TIMEOUT
    assert artifact.metadata.status_code is None
    assert "ConnectTimeout" in (artifact.metadata.error_message or "")
    assert artifact.response is None


def test_json_artifact_writer(tmp_path: Path):
    """驗證檔案寫入器建立目錄與 JSON 落盤正確性"""
    writer = JsonArtifactWriter(base_dir=tmp_path)
    run_dir = writer.create_run_directory("provider_x", "2026-09-29T18:00:00+08:00")

    assert run_dir.exists()
    assert run_dir.is_dir()

    meta = DiagnosticMetadata(
        provider_id="provider_x",
        provider_name="X Provider",
        endpoint_id="list_all",
        domain="community",
        name="清單",
        description="測試",
        status=DiagnosticStatus.SUCCESS,
        status_code=200,
        latency_ms=45.2,
        timestamp="2026-09-29T18:00:00",
    )
    req = DiagnosticRequestSnapshot(
        method="GET",
        url="https://example.com/list",
        headers={"h": "1"},
        params={"p": 1},
    )
    resp = DiagnosticResponseSnapshot(
        status_code=200,
        latency_ms=45.2,
        headers={"h": "2"},
        body={"items": []},
    )
    artifact = DiagnosticArtifact(metadata=meta, request=req, response=resp)

    saved_file = writer.write_artifact(run_dir, artifact)
    assert saved_file.exists()
    assert saved_file.name == "list_all.json"

    # 讀取並檢驗 JSON 結構
    data = json.loads(saved_file.read_text(encoding="utf-8"))
    assert data["metadata"]["endpoint_id"] == "list_all"
    assert data["request"]["method"] == "GET"
    assert data["response"]["status_code"] == 200

    # 寫入 summary
    summary = DiagnosticRunSummary(
        run_id="run_1",
        provider_id="provider_x",
        provider_name="X Provider",
        timestamp="2026-09-29T18:00:00",
        total_endpoints=1,
        successful_endpoints=1,
        failed_endpoints=0,
        total_duration_ms=45.2,
        artifacts=[str(saved_file)],
        endpoints=[meta],
    )
    summary_file = writer.write_summary(run_dir, summary)
    assert summary_file.exists()
    assert summary_file.name == "summary.json"


def test_591_diagnostics_probes():
    """驗證 591 診斷套件與探針定義"""
    provider = Source591Provider()
    diag = provider.diagnostics
    assert diag.provider_id == "591"

    probes = diag.get_probes()
    assert len(probes) == 7

    endpoint_ids = [p.endpoint_id for p in probes]
    assert "health_ping" in endpoint_ids
    assert "community_list" in endpoint_ids
    assert "community_detail" in endpoint_ids
    assert "sale_list" in endpoint_ids
    assert "sale_detail" in endpoint_ids
    assert "new_house_list" in endpoint_ids
    assert "new_house_detail" in endpoint_ids

    # 領域篩選檢驗
    sale_probes = diag.get_probes(domain=DiagnosticDomain.SALE)
    assert len(sale_probes) == 2
    for sp in sale_probes:
        assert sp.domain == DiagnosticDomain.SALE


@pytest.mark.asyncio
async def test_diagnostics_usecase_execution(tmp_path: Path):
    """驗證 DiagnosticsUseCase 批次執行流程與進度通知"""
    mock_probe = MagicMock()
    mock_probe.endpoint_id = "mock_ep"
    mock_probe.domain = DiagnosticDomain.SYSTEM
    mock_probe.name = "Mock Probe"
    mock_probe.description = "Mock Desc"

    meta = DiagnosticMetadata(
        provider_id="mock_prov",
        provider_name="Mock Provider",
        endpoint_id="mock_ep",
        domain="system",
        name="Mock Probe",
        description="Mock Desc",
        status=DiagnosticStatus.SUCCESS,
        status_code=200,
        latency_ms=10.0,
        timestamp="2026-09-29T18:00:00",
    )
    artifact = DiagnosticArtifact(
        metadata=meta,
        request=DiagnosticRequestSnapshot(method="GET", url="https://example.com"),
        response=DiagnosticResponseSnapshot(status_code=200, latency_ms=10.0),
    )
    mock_probe.execute = AsyncMock(return_value=artifact)

    mock_diag = MagicMock()
    mock_diag.provider_id = "mock_prov"
    mock_diag.provider_name = "Mock Provider"
    mock_diag.get_probes.return_value = [mock_probe]

    mock_provider = MagicMock(spec=IHouseSourceProvider)
    mock_provider.provider_id = "mock_prov"
    mock_provider.provider_name = "Mock Provider"
    mock_provider.diagnostics = mock_diag

    custom_registry = ProviderRegistry()
    custom_registry.register_instance(mock_provider)

    writer = JsonArtifactWriter(base_dir=tmp_path)
    use_case = DiagnosticsUseCase(provider_registry=custom_registry, writer=writer)

    progress_calls = []

    def on_progress(probe, art, cur, total):
        progress_calls.append((cur, total))

    summaries = await use_case.run(
        provider_id="mock_prov",
        delay_seconds=0.0,
        on_progress=on_progress,
    )

    assert len(summaries) == 1
    assert summaries[0].total_endpoints == 1
    assert summaries[0].successful_endpoints == 1
    assert summaries[0].failed_endpoints == 0
    assert len(progress_calls) == 1
    assert progress_calls[0] == (1, 1)

    # 驗證落盤目錄檔案
    saved_run_dirs = list(tmp_path.glob("mock_prov/*"))
    assert len(saved_run_dirs) == 1
    assert (saved_run_dirs[0] / "mock_ep.json").exists()
    assert (saved_run_dirs[0] / "summary.json").exists()


@pytest.mark.asyncio
async def test_diagnostics_usecase_run_endpoint_success(tmp_path: Path):
    """驗證 DiagnosticsUseCase.run_endpoint 參數化單端點測試與自訂落盤"""
    mock_probe = MagicMock()
    mock_probe.endpoint_id = "sale_detail"
    mock_probe.domain = DiagnosticDomain.SALE
    mock_probe.name = "中古屋詳細資訊 API"
    mock_probe.description = "測試詳情端點"
    mock_probe.requires_target_id = True
    mock_probe.default_target_id = "20604856"

    meta = DiagnosticMetadata(
        provider_id="mock_prov",
        provider_name="Mock Provider",
        endpoint_id="sale_detail",
        domain="sale",
        name="中古屋詳細資訊 API",
        description="測試詳情端點",
        status=DiagnosticStatus.SUCCESS,
        status_code=200,
        latency_ms=12.5,
        timestamp="2026-10-07T03:00:00",
    )
    artifact = DiagnosticArtifact(
        metadata=meta,
        request=DiagnosticRequestSnapshot(method="GET", url="https://example.com/detail?id=20846137"),
        response=DiagnosticResponseSnapshot(status_code=200, latency_ms=12.5, body={"house_id": "20846137"}),
    )
    mock_probe.execute = AsyncMock(return_value=artifact)

    mock_diag = MagicMock()
    mock_diag.provider_id = "mock_prov"
    mock_diag.provider_name = "Mock Provider"
    mock_diag.get_probe.return_value = mock_probe
    mock_diag.get_probes.return_value = [mock_probe]

    mock_provider = MagicMock(spec=IHouseSourceProvider)
    mock_provider.provider_id = "mock_prov"
    mock_provider.provider_name = "Mock Provider"
    mock_provider.diagnostics = mock_diag

    custom_registry = ProviderRegistry()
    custom_registry.register_instance(mock_provider)

    writer = JsonArtifactWriter(base_dir=tmp_path)
    use_case = DiagnosticsUseCase(provider_registry=custom_registry, writer=writer)

    custom_output = tmp_path / "custom_dir" / "my_custom_sale.json"
    result_artifact, saved_path = await use_case.run_endpoint(
        provider_id="mock_prov",
        endpoint_id="sale_detail",
        target_id="S20846137",
        extra_params={"debug": 1},
        custom_file_path=custom_output,
    )

    assert result_artifact.metadata.status == DiagnosticStatus.SUCCESS
    assert saved_path == custom_output
    assert custom_output.exists()
    content = json.loads(custom_output.read_text(encoding="utf-8"))
    assert content["metadata"]["endpoint_id"] == "sale_detail"
    assert content["response"]["body"]["house_id"] == "20846137"

    # 驗證傳給 probe.execute 的 context
    mock_probe.execute.assert_awaited_once()
    _, kwargs = mock_probe.execute.call_args
    exec_ctx = kwargs.get("context")
    assert exec_ctx is not None
    assert exec_ctx.target_id == "S20846137"
    assert exec_ctx.extra_params == {"debug": 1}


def test_diagnostics_usecase_list_probes():
    """驗證 DiagnosticsUseCase.list_probes 查詢探針清單規格"""
    mock_probe = MagicMock()
    mock_probe.endpoint_id = "sale_detail"
    mock_probe.domain = DiagnosticDomain.SALE

    mock_diag = MagicMock()
    mock_diag.get_probes.return_value = [mock_probe]

    mock_provider = MagicMock(spec=IHouseSourceProvider)
    mock_provider.provider_id = "mock_prov"
    mock_provider.diagnostics = mock_diag

    custom_registry = ProviderRegistry()
    custom_registry.register_instance(mock_provider)

    use_case = DiagnosticsUseCase(provider_registry=custom_registry)
    probes = use_case.list_probes(provider_id="mock_prov")
    assert len(probes) == 1
    p, probe = probes[0]
    assert p.provider_id == "mock_prov"
    assert probe.endpoint_id == "sale_detail"


@pytest.mark.asyncio
async def test_591_sale_detail_probe_target_id_cleaning():
    """驗證 591 SaleHouseDetailProbe 正確清理前綴 S/H 並傳遞至 URL 參數"""
    from src.domain.diagnostics import ProbeExecutionContext
    from src.providers.source_591.diagnostics import SaleHouseDetailProbe

    probe = SaleHouseDetailProbe()
    assert probe.requires_target_id is True
    assert probe.default_target_id == "20604856"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.headers = {}
    mock_resp.json.return_value = {"status": 1}
    mock_client.headers = {}
    mock_client.request.return_value = mock_resp

    # 傳入包含 'S' 前綴的物件 ID
    ctx = ProbeExecutionContext(target_id="S20846137")
    artifact = await probe.execute(mock_client, context=ctx)

    assert artifact.metadata.status == DiagnosticStatus.SUCCESS
    # 檢查請求參數中的 id 是否已去除 S
    assert artifact.request.params["id"] == "20846137"

