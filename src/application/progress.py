"""HouseLensAPI - 同步進度回報器抽象與 Rich 實作 (Progress Reporters)"""

from typing import Any, Dict, Optional, Protocol
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.console import Console

_default_console = Console()


class IProgressReporter(Protocol):
    """進度回報器抽象合約"""

    def on_start(self, domain: str, total: Optional[int] = None) -> None:
        """同步作業啟動"""
        ...

    def on_item_fetched(self, title: str) -> None:
        """單筆資料擷取成功"""
        ...

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        """偵測到重複物件並自動歸戶合併"""
        ...

    def on_item_detail_enriched(self, title: str) -> None:
        """單筆詳細規格補充成功"""
        ...

    def on_error(self, message: str) -> None:
        """發生警告或非致命錯誤"""
        ...

    def on_complete(self, summary_stats: Dict[str, Any]) -> None:
        """作業完成"""
        ...


class SilentProgressReporter:
    """靜音進度回報器 (供 JSON 模式、腳本模式或測試使用)"""

    def on_start(self, domain: str, total: Optional[int] = None) -> None:
        pass

    def on_item_fetched(self, title: str) -> None:
        pass

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        pass

    def on_item_detail_enriched(self, title: str) -> None:
        pass

    def on_error(self, message: str) -> None:
        pass

    def on_complete(self, summary_stats: Dict[str, Any]) -> None:
        pass


class RichProgressReporter:
    """Rich 互動式彩色進度條實作"""

    def __init__(self, console: Optional[Console] = None):
        target_console = console or _default_console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("[yellow]•[/yellow]"),
            TimeElapsedColumn(),
            console=target_console,
            transient=False,
        )
        self.task_id: Optional[TaskID] = None
        self.duplicates_count = 0
        self.details_count = 0

    def __enter__(self):
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()

    def on_start(self, domain: str, total: Optional[int] = None) -> None:
        self.task_id = self.progress.add_task(
            f"正在同步 {domain} 資料...",
            total=total or 100,
        )

    def on_item_fetched(self, title: str) -> None:
        if self.task_id is not None:
            short_title = title[:20] + "..." if len(title) > 20 else title
            self.progress.update(
                self.task_id,
                advance=1,
                description=f"擷取: {short_title}",
            )

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        self.duplicates_count += 1
        short_title = title[:15] + "..." if len(title) > 15 else title
        self.progress.console.print(
            f"  [bold magenta][去重合併][/bold magenta] -> [white]{short_title}[/white] "
            f"歸戶至實體 [dim]{matched_id[:8]}...[/dim]"
        )

    def on_item_detail_enriched(self, title: str) -> None:
        self.details_count += 1

    def on_error(self, message: str) -> None:
        self.progress.console.print(f"  [bold red][警告]:[/bold red] {message}")

    def on_complete(self, summary_stats: Dict[str, Any]) -> None:
        total = summary_stats.get("total", 0)
        dups = summary_stats.get("duplicates", self.duplicates_count)
        details = summary_stats.get("details", self.details_count)
        self.progress.console.print(
            f"[bold green][OK] 同步完成！[/bold green] 共入庫 [bold cyan]{total}[/bold cyan] 筆實體 "
            f"(其中 [bold magenta]{dups}[/bold magenta] 處刊登去重合併，"
            f"[bold yellow]{details}[/bold yellow] 筆豐富規格)"
        )

