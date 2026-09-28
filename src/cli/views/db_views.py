"""HouseLensAPI - 資料庫狀態與統計 Rich 儀表板視圖 (Database Views)"""

from typing import Any, Dict
from rich import box
from rich.panel import Panel
from rich.table import Table


def render_db_stats_dashboard(stats: Dict[str, Any]) -> Panel:
    """渲染資料庫統計儀表板"""
    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold yellow")
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="bold white")

    # 指標格式化
    total_comms = stats.get("total_communities", 0)
    total_props = stats.get("total_properties", 0)
    total_listings = stats.get("total_listings", 0)
    total_nhs = stats.get("total_new_houses", 0)
    db_size_mb = stats.get("db_size_mb", 0.0)
    db_url = stats.get("db_url", "-")
    dedup_ratio = stats.get("dedup_ratio_pct", 0.0)

    grid.add_row("連線位置:", db_url, "檔案容量:", f"{db_size_mb:.2f} MB")
    grid.add_row("庫存社區節點:", f"{total_comms:,} 筆", "新建案總數:", f"{total_nhs:,} 案")
    grid.add_row("客觀房屋實體:", f"[bold green]{total_props:,} 戶[/bold green]", "平台來源刊登數:", f"[bold magenta]{total_listings:,} 筆[/bold magenta]")

    # 去重分析
    dedup_msg = f"[bold yellow]{dedup_ratio:.1f}%[/bold yellow] (多平台重複刊登已自動歸戶合併)"
    grid.add_row("去重合併率:", dedup_msg, "實體聚合比:", f"平均 1 實體對應 {total_listings / max(total_props, 1):.2f} 處刊登")

    panel = Panel(
        grid,
        title="📊 HouseLens 資料庫健康度與統計儀表板",
        border_style="green",
        box=box.ROUNDED,
    )
    return panel
