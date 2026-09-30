"""HouseLensAPI - API 診斷與探針測試終端視圖 (Diagnostic Views)

以極簡純粹 ANSI 邊框表格呈現 API 測試狀態、狀態碼、延遲時間與落盤路徑。
嚴格遵守零裝飾性符號 (Zero Emoji) 規範。
"""

from typing import List
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.domain.diagnostics import (
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
