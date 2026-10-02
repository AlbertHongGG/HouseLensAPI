"""HouseLensAPI - 同步進度回報器抽象與 Rich 實作 (Progress Reporters)

規範階段劃分 (清單探索 -> 併發詳情 -> 消歧入庫)，保證進度條生命週期嚴格閉環，
杜絕終端輸出倒置問題，並透過 sanitize_terminal_text 確保零 Emoji 與 Windows 編碼穩定性。
"""

from typing import Any, Dict, Optional, Protocol
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from src.application.text_sanitizer import sanitize_terminal_text

_default_console = Console()


class IEnrichmentTracker(Protocol):
    """併發詳情規格補齊追蹤器協定"""

    def advance(self, title: str) -> None:
        """單筆項目詳情擷取推進"""
        ...

    def enriched(self, title: str) -> None:
        """單筆項目詳細規格補齊成功"""
        ...

    def on_error(self, message: str) -> None:
        """單筆項目擷取發生錯誤"""
        ...

    def close(self) -> None:
        """完成並銷毀進度條生命週期"""
        ...


class IProgressReporter(Protocol):
    """同步進度回報器抽象合約"""

    def on_domain_start(self, domain: str, current_domain: int = 1, total_domains: int = 1) -> None:
        """領域同步啟動標識"""
        ...

    def on_discovery_start(self, target_count: Optional[int] = None) -> None:
        """階段 1: 開始清單探索"""
        ...

    def on_discovery_page(
        self,
        page: int,
        page_items_count: int,
        accumulated_count: int,
        target_count: Optional[int] = None,
    ) -> None:
        """階段 1: 取得單頁清單回報"""
        ...

    def on_discovery_complete(self, total_discovered: int) -> None:
        """階段 1: 清單探索完成"""
        ...

    def start_enrichment(self, total: int, description: str = "詳情規格補齊") -> IEnrichmentTracker:
        """階段 2: 啟動併發詳情補齊追蹤器"""
        ...

    def on_persistence_start(self) -> None:
        """階段 3: 開始消歧入庫"""
        ...

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        """階段 3: 偵測到重複刊登並自動歸戶合併"""
        ...

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        """領域同步作業完成統計面板"""
        ...

    def on_error(self, message: str) -> None:
        """全域警告或非致命錯誤"""
        ...


class SilentEnrichmentTracker:
    """靜音版詳情追蹤器"""

    def advance(self, title: str) -> None:
        pass

    def enriched(self, title: str) -> None:
        pass

    def on_error(self, message: str) -> None:
        pass

    def close(self) -> None:
        pass


class SilentProgressReporter:
    """靜音進度回報器 (供 JSON 模式、腳本模式或測試使用)"""

    def on_domain_start(self, domain: str, current_domain: int = 1, total_domains: int = 1) -> None:
        pass

    def on_discovery_start(self, target_count: Optional[int] = None) -> None:
        pass

    def on_discovery_page(
        self,
        page: int,
        page_items_count: int,
        accumulated_count: int,
        target_count: Optional[int] = None,
    ) -> None:
        pass

    def on_discovery_complete(self, total_discovered: int) -> None:
        pass

    def start_enrichment(self, total: int, description: str = "詳情規格補齊") -> IEnrichmentTracker:
        return SilentEnrichmentTracker()

    def on_persistence_start(self) -> None:
        pass

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        pass

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        pass

    def on_error(self, message: str) -> None:
        pass


class RichEnrichmentTracker:
    """Rich 詳情併發進度條追蹤器 (生命週期僅存活於階段 2)"""

    def __init__(self, console: Console, total: int, description: str = "擷取詳情"):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("[yellow]•[/yellow]"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        self.progress.start()
        self.task_id: TaskID = self.progress.add_task(description, total=total)

    def advance(self, title: str) -> None:
        clean_title = sanitize_terminal_text(title, max_len=24)
        self.progress.update(
            self.task_id,
            advance=1,
            description=f"擷取: {clean_title}",
        )

    def enriched(self, title: str) -> None:
        pass

    def on_error(self, message: str) -> None:
        clean_msg = sanitize_terminal_text(message)
        self.progress.console.print(f"    [bold red][警告]:[/bold red] {clean_msg}")

    def close(self) -> None:
        """詳情階段結束，立即關閉並銷毀進度條"""
        self.progress.stop()


class RichProgressReporter:
    """Rich 結構化互動式終端日誌回報器"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or _default_console
        self.current_domain: str = ""
        self.duplicates_count: int = 0
        self.details_count: int = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def on_domain_start(self, domain: str, current_domain: int = 1, total_domains: int = 1) -> None:
        self.current_domain = domain
        self.duplicates_count = 0
        self.details_count = 0
        self.console.print(
            f"\n[bold cyan]--------------------------------------------------------------------------------[/bold cyan]\n"
            f"[bold cyan][領域 {current_domain}/{total_domains}: {domain}領域同步作業][/bold cyan]"
        )

    def on_discovery_start(self, target_count: Optional[int] = None) -> None:
        target_desc = f"{target_count} 筆" if target_count is not None else "全量同步 (直至來源耗盡)"
        self.console.print(f"  [bold yellow][階段 1/3: 清單探索][/bold yellow] 開始分頁巡訪 (目標: {target_desc})...")

    def on_discovery_page(
        self,
        page: int,
        page_items_count: int,
        accumulated_count: int,
        target_count: Optional[int] = None,
    ) -> None:
        progress_str = f"{accumulated_count}/{target_count}" if target_count is not None else f"{accumulated_count}"
        self.console.print(
            f"    -> 第 [bold white]{page}[/bold white] 頁取得 [bold cyan]{page_items_count}[/bold cyan] 筆 "
            f"| 目前累積有效物件: [bold green]{progress_str}[/bold green] 筆"
        )

    def on_discovery_complete(self, total_discovered: int) -> None:
        self.console.print(
            f"  [bold yellow][階段 1/3: 清單探索][/bold yellow] 探索完成，共取得 [bold cyan]{total_discovered}[/bold cyan] 筆標準物件清單。"
        )

    def start_enrichment(self, total: int, description: str = "詳情規格補齊") -> IEnrichmentTracker:
        self.console.print(f"  [bold yellow][階段 2/3: 併發詳情][/bold yellow] 啟動併發詳情補齊 (共 [bold cyan]{total}[/bold cyan] 筆)...")
        return RichEnrichmentTracker(console=self.console, total=total, description=description)

    def on_persistence_start(self) -> None:
        self.console.print("  [bold yellow][階段 3/3: 消歧入庫][/bold yellow] 正在進行跨來源去重消歧與資料庫原子寫入...")

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        self.duplicates_count += 1
        clean_title = sanitize_terminal_text(title, max_len=20)
        self.console.print(
            f"    [bold magenta][去重合併][/bold magenta] -> [white]{clean_title}[/white] "
            f"歸戶至既有實體 [dim]{matched_id[:8]}...[/dim]"
        )

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        total = summary_stats.get("total", 0)
        dups = summary_stats.get("duplicates", self.duplicates_count)
        details = summary_stats.get("details", self.details_count)
        domain_name = summary_stats.get("domain", self.current_domain or "資料")
        self.console.print(
            f"  [bold green][OK] {domain_name}領域同步完成！[/bold green] "
            f"共入庫 [bold cyan]{total}[/bold cyan] 筆實體 "
            f"(其中 [bold magenta]{dups}[/bold magenta] 處刊登去重合併，"
            f"[bold yellow]{details}[/bold yellow] 筆豐富規格)"
        )

    def on_error(self, message: str) -> None:
        clean_msg = sanitize_terminal_text(message)
        self.console.print(f"  [bold red][警告]:[/bold red] {clean_msg}")
