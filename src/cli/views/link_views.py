"""HouseLensAPI - 社區消歧與外鍵補齊 Rich 視圖 (Community Link Views)"""

from typing import Any, Dict
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.services.community_resolver import CommunityResolutionReport, MatchStatus


def render_community_link_dashboard(report: CommunityResolutionReport, is_dry_run: bool = False) -> Panel:
    """渲染社區消歧與關聯統計儀表板"""
    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold yellow")
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")

    mode_str = "[bold magenta][乾跑預演模式 (DRY-RUN)][/bold magenta]" if is_dry_run else "[bold green][實際寫入模式][/bold green]"

    grid.add_row("執行模式:", mode_str, "執行總耗時:", f"{report.elapsed_seconds:.2f} 秒")
    grid.add_row("掃描房屋實體:", f"{report.scanned_properties_count:,} 戶", "聚合社區目標:", f"{report.distinct_targets_count:,} 個")
    grid.add_row(
        "本地直接對齊:",
        f"[bold green]{report.locally_linked_properties_count:,} 戶[/bold green]",
        "遠端探索補齊:",
        f"[bold cyan]{report.remotely_resolved_properties_count:,} 戶 ({report.persisted_communities_count} 社區)[/bold cyan]",
    )
    grid.add_row(
        "多候選歧義略過:",
        f"[bold yellow]{report.ambiguous_targets_count:,} 個[/bold yellow]",
        "遠端查無結果:",
        f"[dim]{report.not_found_targets_count:,} 個[/dim]",
    )
    if report.skipped_no_community_count > 0:
        grid.add_row("無社區實體略過:", f"[dim]{report.skipped_no_community_count:,} 戶 (獨立透天/老公寓)[/dim]", "", "")

    panel = Panel(
        grid,
        title="HouseLens 中古屋社區消歧與兩階段補齊儀表板",
        border_style="cyan",
        box=box.ROUNDED,
    )
    return panel


def render_community_link_details_table(report: CommunityResolutionReport) -> Table:
    """渲染每個目標社區消歧明細表格"""
    table = Table(
        title="社區對齊與消歧處理明細清單",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("目標社區名稱 / ID", style="bold white")
    table.add_column("行政區域", style="dim")
    table.add_column("關聯房屋數", justify="right")
    table.add_column("對齊狀態", justify="center")
    table.add_column("命中外部代碼", style="bold yellow")
    table.add_column("消歧結果與說明", style="dim")

    for d in report.details:
        status_val = d.get("status")
        if status_val == MatchStatus.LOCAL_LINKED.value:
            status_badge = "[bold green]本地對齊[/bold green]"
        elif status_val == MatchStatus.REMOTE_RESOLVED.value:
            status_badge = "[bold cyan]遠端補齊[/bold cyan]"
        elif status_val == MatchStatus.AMBIGUOUS.value:
            status_badge = "[bold yellow]歧義略過[/bold yellow]"
        elif status_val == MatchStatus.NOT_FOUND.value:
            status_badge = "[dim]查無社區[/dim]"
        else:
            status_badge = f"[dim]{status_val}[/dim]"

        table.add_row(
            str(d.get("target_name") or "-"),
            str(d.get("region") or "-"),
            f"{d.get('properties_count', 0)} 戶",
            status_badge,
            str(d.get("matched_external_id") or "-"),
            str(d.get("reason") or "-"),
        )

    return table
