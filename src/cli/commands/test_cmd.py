"""HouseLensAPI CLI - 來源 API 診斷與探針檢測命令 (Test Commands)

依序測試目標 Provider 的所有 API 端點，錄製完整 Request/Response/Metadata，
並以結構化 JSON 檔落盤至 .tmp/api_diagnostics/ 目錄。
嚴格遵守零裝飾性符號 (Zero Emoji) 規範。
"""

import asyncio
from pathlib import Path
from typing import Optional
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
)
from src.core.interfaces.diagnostics import IProbeEndpoint
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    DiagnosticStatus,
)
import src.providers  # 自動載入並註冊所有可用 provider

def run_api_diagnostics_cmd(
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
    """執行各 Provider API 探針檢測與全流量封包錄製"""

    # 領域過濾解析
    diag_domain: Optional[DiagnosticDomain] = None
    if domain:
        norm_domain = domain.strip().lower()
        domain_mapping = {
            "community": DiagnosticDomain.COMMUNITY,
            "sale": DiagnosticDomain.SALE,
            "newhouse": DiagnosticDomain.NEW_HOUSE,
            "system": DiagnosticDomain.SYSTEM,
        }
        if norm_domain not in domain_mapping:
            print_error(f"不支援的領域: '{domain}'。有效值為: {list(domain_mapping.keys())}")
            raise typer.Exit(code=1)
        diag_domain = domain_mapping[norm_domain]

    use_case = DiagnosticsUseCase()

    # 即時終端進度回呼 (純文字，無 emoji)
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
        print_info(f"啟動 API 診斷探針測試: {target_name} (冷卻間隔: {delay:.1f}s)")

    try:
        summaries = asyncio.run(
            use_case.run(
                provider_id=provider_id,
                domain=diag_domain,
                delay_seconds=delay,
                on_progress=on_progress if format_opt == "text" else None,
            )
        )
    except Exception as exc:
        print_error(f"診斷流程執行失敗: {exc}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [s.model_dump() for s in summaries]
        print_json_data(data)
        return

    # 文字格式終端呈現
    console.print()
    for summary in summaries:
        table = render_diagnostic_summary_table(summary)
        console.print(table)
        console.print()

    overview = render_diagnostic_overview_panel(summaries)
    console.print(overview)

    # 輸出落盤目錄位置
    first_summary = summaries[0] if summaries else None
    if first_summary and first_summary.artifacts:
        sample_path = first_summary.artifacts[0]
        run_folder = str(Path(sample_path).parent)
        print_success(f"完整 HTTP Request/Response/Metadata 封包已保存至: {run_folder}")

    # 若有失敗端點，退出碼設為 1 以利自動化測試/CI 檢測
    has_failure = any(s.failed_endpoints > 0 for s in summaries)
    if has_failure:
        raise typer.Exit(code=1)
