"""HouseLensAPI CLI - 來源 API 診斷與探針檢測命令群組 (Test Commands)

提供 API 端點功能性測試、流量封包錄製與全端點套件健康度檢測。
嚴格遵守零裝飾性符號 (Zero Emoji) 規範。
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional
import typer

from src.application.diagnostics_usecase import DiagnosticsUseCase
from src.cli.views.console import (
    console,
    print_error,
    print_info,
    print_json_data,
    print_success,
)
from src.cli.views.diagnostic_views import (
    render_diagnostic_overview_panel,
    render_diagnostic_summary_table,
    render_probe_request_panel,
    render_probe_response_viewer,
    render_probes_list_table,
    render_single_probe_overview_panel,
)
from src.core.interfaces.diagnostics import IProbeEndpoint
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    DiagnosticStatus,
)
import src.providers  # 自動載入並註冊所有可用 provider

test_app = typer.Typer(
    name="test",
    help="來源 Provider 之 API 診斷、單端點功能測試與全流量封包錄製",
    no_args_is_help=True,
)
test_app.__test__ = False



def _parse_domain(domain_str: Optional[str]) -> Optional[DiagnosticDomain]:
    """解析字串領域參數為 DiagnosticDomain 列舉"""
    if not domain_str:
        return None
    norm = domain_str.strip().lower()
    domain_mapping = {
        "community": DiagnosticDomain.COMMUNITY,
        "sale": DiagnosticDomain.SALE,
        "newhouse": DiagnosticDomain.NEW_HOUSE,
        "system": DiagnosticDomain.SYSTEM,
    }
    if norm not in domain_mapping:
        print_error(f"不支援的領域: '{domain_str}'。有效值為: {list(domain_mapping.keys())}")
        raise typer.Exit(code=1)
    return domain_mapping[norm]


@test_app.command(
    "endpoint",
    help="測試單一 API 端點之實際功能回傳，支援自訂 target_id 與額外參數，並錄製原始封包",
)
def run_single_endpoint_cmd(
    provider_id: str = typer.Argument(
        ...,
        help="目標來源代碼 (例如 '591')",
    ),
    endpoint_id: str = typer.Argument(
        ...,
        help="目標端點代碼 (例如 'sale_detail', 'community_detail')",
    ),
    target_id: Optional[str] = typer.Option(
        None,
        "--target-id",
        "-i",
        help="目標物件/實體 ID (例如中古屋 'S20846137'、社區 '5855864')",
    ),
    params: Optional[str] = typer.Option(
        None,
        "--params",
        "-p",
        help="自訂 Query 參數 (JSON 字串，例如 '{\"regionid\": 1}')",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="自訂完整封包 JSON 儲存路徑",
    ),
    format_opt: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="輸出格式: text 或 json",
    ),
    show_body: bool = typer.Option(
        True,
        "--show-body/--no-show-body",
        help="在 text 模式下是否於終端顯示 Response Body 預覽",
    ),
):
    """執行單一 API 端點之參數化功能測試與封包捕捉"""
    parsed_params: Dict[str, Any] = {}
    if params:
        try:
            parsed_params = json.loads(params)
            if not isinstance(parsed_params, dict):
                print_error(f"--params 必須為 JSON 字典物件格式，傳入為: {type(parsed_params).__name__}")
                raise typer.Exit(code=1)
        except json.JSONDecodeError as exc:
            print_error(f"--params 格式錯誤，非合法 JSON: {exc}")
            raise typer.Exit(code=1)

    custom_path: Optional[Path] = Path(output_file).resolve() if output_file else None
    use_case = DiagnosticsUseCase()

    if format_opt == "text":
        tid_display = f" [目標 ID: {target_id}]" if target_id else ""
        print_info(f"啟動單端點功能測試: 來源 '{provider_id}' -> 端點 '{endpoint_id}'{tid_display}")

    try:
        artifact, saved_path = asyncio.run(
            use_case.run_endpoint(
                provider_id=provider_id,
                endpoint_id=endpoint_id,
                target_id=target_id,
                extra_params=parsed_params,
                custom_file_path=custom_path,
            )
        )
    except Exception as exc:
        print_error(f"單端點測試執行失敗: {exc}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        print_json_data(artifact.model_dump())
        return

    # Text 排版顯示
    console.print()
    overview_panel = render_single_probe_overview_panel(artifact, saved_path)
    console.print(overview_panel)
    console.print()

    req_panel = render_probe_request_panel(artifact)
    console.print(req_panel)
    console.print()

    if show_body:
        resp_panel = render_probe_response_viewer(artifact)
        console.print(resp_panel)
        console.print()

    print_success(f"完整 HTTP Request/Response/Metadata 封包已保存至: {saved_path}")

    if artifact.metadata.status != DiagnosticStatus.SUCCESS:
        raise typer.Exit(code=1)


@test_app.command(
    "suite",
    help="依序執行目標 Provider 之探針套件健康檢測與批次流量錄製",
)
def run_api_diagnostics_suite_cmd(
    provider_id: Optional[str] = typer.Argument(
        None,
        help="目標來源外掛代碼 (例如 '591')，留空則依序測試所有已註冊來源",
    ),
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="業務領域過濾: community, sale, newhouse, system",
    ),
    delay: float = typer.Option(
        1.0,
        "--delay",
        min=0.0,
        max=30.0,
        help="各端點調用間冷卻秒數 (預設: 1.0 秒)",
    ),
    format_opt: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="輸出格式: text 或 json",
    ),
):
    """執行 Provider API 探針套件檢測與全流量封包錄製"""
    diag_domain = _parse_domain(domain)
    use_case = DiagnosticsUseCase()

    def on_progress(probe: IProbeEndpoint, artifact: DiagnosticArtifact, cur: int, total: int):
        if format_opt == "text":
            status_text = (
                "[green]PASS[/green]"
                if artifact.metadata.status == DiagnosticStatus.SUCCESS
                else "[red]FAIL[/red]"
            )
            lat_text = f"{artifact.metadata.latency_ms:.1f}ms"
            code_text = str(artifact.metadata.status_code) if artifact.metadata.status_code else "-"
            console.print(
                f"  [{cur}/{total}] [{code_text}] {probe.name:<18} -> {status_text} ({lat_text})"
            )

    if format_opt == "text":
        target_name = provider_id if provider_id else "所有已註冊來源"
        print_info(f"啟動 API 診斷套件測試: {target_name} (冷卻間隔: {delay:.1f}s)")

    try:
        summaries = asyncio.run(
            use_case.run_suite(
                provider_id=provider_id,
                domain=diag_domain,
                delay_seconds=delay,
                on_progress=on_progress if format_opt == "text" else None,
            )
        )
    except Exception as exc:
        print_error(f"診斷套件執行失敗: {exc}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [s.model_dump() for s in summaries]
        print_json_data(data)
        return

    console.print()
    for summary in summaries:
        table = render_diagnostic_summary_table(summary)
        console.print(table)
        console.print()

    overview = render_diagnostic_overview_panel(summaries)
    console.print(overview)

    first_summary = summaries[0] if summaries else None
    if first_summary and first_summary.artifacts:
        sample_path = first_summary.artifacts[0]
        run_folder = str(Path(sample_path).parent)
        print_success(f"完整 HTTP Request/Response/Metadata 封包已保存至: {run_folder}")

    has_failure = any(s.failed_endpoints > 0 for s in summaries)
    if has_failure:
        raise typer.Exit(code=1)


@test_app.command(
    "list",
    help="列出指定來源 (或所有來源) 支援之診斷探針端點規格與參數需求",
)
def list_probes_cmd(
    provider_id: Optional[str] = typer.Argument(
        None,
        help="目標來源外掛代碼 (例如 '591')，留空則列出所有來源",
    ),
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="業務領域過濾: community, sale, newhouse, system",
    ),
    format_opt: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="輸出格式: text 或 json",
    ),
):
    """查詢已註冊之來源與探針規格清單"""
    diag_domain = _parse_domain(domain)
    use_case = DiagnosticsUseCase()

    try:
        probes_data = use_case.list_probes(provider_id=provider_id, domain=diag_domain)
    except Exception as exc:
        print_error(f"查詢探針清單失敗: {exc}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [
            {
                "provider_id": provider.provider_id,
                "provider_name": provider.provider_name,
                "endpoint_id": probe.endpoint_id,
                "domain": probe.domain.value,
                "name": probe.name,
                "requires_target_id": probe.requires_target_id,
                "default_target_id": probe.default_target_id,
                "description": probe.description,
            }
            for provider, probe in probes_data
        ]
        print_json_data(data)
        return

    table = render_probes_list_table(probes_data)
    console.print(table)


# 向後相容別名
run_api_diagnostics_cmd = run_api_diagnostics_suite_cmd

