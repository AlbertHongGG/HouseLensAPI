import json
from pathlib import Path
from typing import List, Optional
from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.core.interfaces.diagnostics import IProbeEndpoint
from src.core.interfaces.provider import IHouseSourceProvider
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticRunSummary,
    DiagnosticStatus,
)


def render_diagnostic_summary_table(summary: DiagnosticRunSummary) -> Table:
    """渲染單一 Provider 批次診斷測試結果表格"""
    table = Table(
        title=f"API 診斷測試結果: {summary.provider_name} [{summary.provider_id}]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("端點代碼 (ID)", style="bold yellow", no_wrap=True)
    table.add_column("領域", style="cyan", no_wrap=True)
    table.add_column("端點名稱", style="bold white")
    table.add_column("HTTP", justify="center", style="bold")
    table.add_column("延遲 (ms)", justify="right")
    table.add_column("判定結果", justify="center")
    table.add_column("錯誤訊息 / 備註", style="dim")

    for meta in summary.endpoints:
        # HTTP 狀態碼樣式
        if meta.status_code is not None:
            if 200 <= meta.status_code < 300:
                http_str = f"[bold green]{meta.status_code}[/bold green]"
            elif 400 <= meta.status_code < 500:
                http_str = f"[bold yellow]{meta.status_code}[/bold yellow]"
            else:
                http_str = f"[bold red]{meta.status_code}[/bold red]"
        else:
            http_str = "[dim]-[/dim]"

        # 判定結果徽章 (嚴禁 Emoji)
        if meta.status == DiagnosticStatus.SUCCESS:
            badge = "[bold green]PASS[/bold green]"
        elif meta.status == DiagnosticStatus.TIMEOUT:
            badge = "[bold yellow]TIMEOUT[/bold yellow]"
        elif meta.status == DiagnosticStatus.NETWORK_ERROR:
            badge = "[bold red]NET_ERR[/bold red]"
        else:
            badge = "[bold red]FAIL[/bold red]"

        # 延遲格式化
        if meta.latency_ms > 0:
            if meta.latency_ms < 500:
                lat_str = f"[green]{meta.latency_ms:.1f}[/green]"
            elif meta.latency_ms < 1500:
                lat_str = f"[yellow]{meta.latency_ms:.1f}[/yellow]"
            else:
                lat_str = f"[red]{meta.latency_ms:.1f}[/red]"
        else:
            lat_str = "-"

        err_note = meta.error_message or "-"
        if len(err_note) > 40:
            err_note = err_note[:37] + "..."

        table.add_row(
            meta.endpoint_id,
            meta.domain,
            meta.name,
            http_str,
            lat_str,
            badge,
            err_note,
        )

    return table


def render_diagnostic_overview_panel(summaries: List[DiagnosticRunSummary]) -> Panel:
    """渲染所有受測來源之批次總結面板"""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")

    total_endpoints = sum(s.total_endpoints for s in summaries)
    total_passed = sum(s.successful_endpoints for s in summaries)
    total_failed = sum(s.failed_endpoints for s in summaries)
    total_time_ms = sum(s.total_duration_ms for s in summaries)

    grid.add_row(
        "受測平台總數:", f"{len(summaries)} 個",
        "總測試端點數:", f"{total_endpoints} 個",
    )
    grid.add_row(
        "成功通過端點:", f"[bold green]{total_passed} 個[/bold green]",
        "異常失敗端點:", f"[bold red]{total_failed} 個[/bold red]" if total_failed > 0 else "[green]0 個[/green]",
    )
    grid.add_row(
        "累計連線耗時:", f"{total_time_ms:.1f} ms",
        "落盤記錄路徑:", "[dim].tmp/api_diagnostics/...[/dim]",
    )

    border_color = "green" if total_failed == 0 else "red"
    return Panel(
        grid,
        title="API 診斷測試總結報告",
        border_style=border_color,
        box=box.ROUNDED,
    )


def render_single_probe_overview_panel(
    artifact: DiagnosticArtifact,
    saved_path: Path,
) -> Panel:
    """渲染單一端點測試概覽面板"""
    meta = artifact.metadata
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")

    status_str = (
        "[bold green]PASS[/bold green]"
        if meta.status == DiagnosticStatus.SUCCESS
        else f"[bold red]{meta.status.value}[/bold red]"
    )
    code_str = (
        f"[bold green]{meta.status_code}[/bold green]"
        if meta.status_code and 200 <= meta.status_code < 300
        else (f"[bold red]{meta.status_code}[/bold red]" if meta.status_code else "-")
    )

    grid.add_row(
        "來源平台:", f"{meta.provider_name} [{meta.provider_id}]",
        "業務領域:", meta.domain,
    )
    grid.add_row(
        "端點代碼:", f"[bold yellow]{meta.endpoint_id}[/bold yellow]",
        "端點名稱:", meta.name,
    )
    grid.add_row(
        "HTTP 狀態:", code_str,
        "連線延遲:", f"{meta.latency_ms:.1f} ms",
    )
    grid.add_row(
        "測試結果:", status_str,
        "測試時間:", meta.timestamp,
    )
    grid.add_row(
        "請求連線:", f"[cyan]{artifact.request.method}[/cyan] {artifact.request.url}",
        "落盤檔案:", f"[dim]{saved_path}[/dim]",
    )

    if meta.error_message:
        grid.add_row("錯誤備註:", f"[bold red]{meta.error_message}[/bold red]", "", "")

    border_color = "green" if meta.status == DiagnosticStatus.SUCCESS else "red"
    return Panel(
        grid,
        title=f"端點診斷檢測: {meta.name} [{meta.endpoint_id}]",
        border_style=border_color,
        box=box.ROUNDED,
    )


def render_probe_request_panel(artifact: DiagnosticArtifact) -> Panel:
    """渲染送出之 HTTP 請求詳情面板"""
    req = artifact.request
    req_dict = {
        "method": req.method,
        "url": req.url,
        "params": req.params,
        "headers": req.headers,
        "body": req.body,
    }
    json_text = json.dumps(req_dict, indent=2, ensure_ascii=False)
    syntax = Syntax(json_text, "json", theme="monokai", word_wrap=True)
    return Panel(
        syntax,
        title="HTTP 請求封包快照 (Request)",
        border_style="cyan",
        box=box.ROUNDED,
    )


def render_probe_response_viewer(
    artifact: DiagnosticArtifact,
    max_lines: int = 50,
) -> Panel:
    """渲染接收之 HTTP 回應封包預覽面板 (支援 JSON 語法高亮與行數限制)"""
    resp = artifact.response
    if not resp:
        return Panel(
            "[dim]無 HTTP 回應資料 (可能為逾時或網路錯誤)[/dim]",
            title="HTTP 回應封包 (Response)",
            border_style="red",
            box=box.ROUNDED,
        )

    body_obj = resp.body
    if isinstance(body_obj, (dict, list)):
        raw_text = json.dumps(body_obj, indent=2, ensure_ascii=False)
    else:
        raw_text = str(body_obj) if body_obj is not None else ""

    lines = raw_text.splitlines()
    truncated = False
    if len(lines) > max_lines:
        display_text = "\n".join(lines[:max_lines]) + f"\n\n... [截斷顯示: 共 {len(lines)} 行，完整內容請參閱落盤 JSON 檔案]"
        truncated = True
    else:
        display_text = raw_text

    syntax = Syntax(display_text, "json" if isinstance(body_obj, (dict, list)) else "text", theme="monokai", word_wrap=True)
    return Panel(
        syntax,
        title=f"HTTP 回應主體 (Response Body - 狀態碼: {resp.status_code})",
        border_style="green" if 200 <= resp.status_code < 300 else "yellow",
        box=box.ROUNDED,
    )


def render_probes_list_table(
    probes_data: List[tuple[IHouseSourceProvider, IProbeEndpoint]],
) -> Table:
    """渲染已註冊探針清單表格"""
    table = Table(
        title="已註冊 API 診斷探針端點清單",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("來源代碼", style="cyan", no_wrap=True)
    table.add_column("端點代碼 (ID)", style="bold yellow", no_wrap=True)
    table.add_column("領域", style="magenta", no_wrap=True)
    table.add_column("端點名稱", style="bold white")
    table.add_column("Target ID 支援", justify="center")
    table.add_column("預設測試 ID", style="dim", justify="center")
    table.add_column("功能說明", style="white")

    for provider, probe in probes_data:
        target_id_str = (
            "[bold green]支援[/bold green]"
            if probe.requires_target_id
            else "[dim]否[/dim]"
        )
        default_id_str = probe.default_target_id or "-"
        table.add_row(
            provider.provider_id,
            probe.endpoint_id,
            probe.domain.value,
            probe.name,
            target_id_str,
            default_id_str,
            probe.description,
        )

    return table

