"""HouseLensAPI - 串流進度回報器抽象與 Rich 實作 (Streaming Progress Reporters)

專為串流式分頁微批次設計，即時滾動輸出單頁進度 (探索數、新物件數、跳過數、累計入庫數)，
支援優雅中斷提示，並透過 sanitize_terminal_text 確保零 Emoji 與 Windows 編碼穩定性。
"""

from typing import Any, Dict, Optional, Protocol
from rich.console import Console

from src.application.streaming_pipeline import PageProcessStats
from src.application.text_sanitizer import sanitize_terminal_text

_default_console = Console()


class IProgressReporter(Protocol):
    """串流同步進度回報器抽象合約"""

    def on_domain_start(
        self,
        domain: str,
        current_domain: int = 1,
        total_domains: int = 1,
        target_count: Optional[int] = None,
    ) -> None:
        """領域同步啟動標識"""
        ...

    def on_page_processed(self, stats: PageProcessStats) -> None:
        """單頁微批次處理完成即時回報"""
        ...

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        """偵測到重複刊登並自動歸戶合併"""
        ...

    def on_item_fetching(self, title: str) -> None:
        """單筆詳情擷取推進"""
        ...

    def on_interrupted(self, accumulated_count: int, domain_name: str) -> None:
        """使用者中斷時的安全退出提示"""
        ...

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        """領域同步作業完成統計面板"""
        ...

    def on_error(self, message: str) -> None:
        """全域警告或非致命錯誤"""
        ...


class SilentProgressReporter:
    """靜音進度回報器 (供 JSON 模式、腳本模式或單元測試使用)"""

    def on_domain_start(
        self,
        domain: str,
        current_domain: int = 1,
        total_domains: int = 1,
        target_count: Optional[int] = None,
    ) -> None:
        pass

    def on_page_processed(self, stats: PageProcessStats) -> None:
        pass

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        pass

    def on_item_fetching(self, title: str) -> None:
        pass

    def on_interrupted(self, accumulated_count: int, domain_name: str) -> None:
        pass

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        pass

    def on_error(self, message: str) -> None:
        pass


class RichProgressReporter:
    """Rich 結構化串流終端日誌回報器"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or _default_console
        self.current_domain: str = ""
        self.duplicates_count: int = 0
        self.total_skipped: int = 0
        self.total_pages: int = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def on_domain_start(
        self,
        domain: str,
        current_domain: int = 1,
        total_domains: int = 1,
        target_count: Optional[int] = None,
    ) -> None:
        self.current_domain = domain
        self.duplicates_count = 0
        self.total_skipped = 0
        self.total_pages = 0
        target_desc = f"{target_count} 筆" if target_count is not None else "全量同步 (直至來源耗盡)"
        self.console.print(
            f"\n[bold cyan]--------------------------------------------------------------------------------[/bold cyan]\n"
            f"[bold cyan][領域 {current_domain}/{total_domains}: {domain}領域串流同步作業][/bold cyan] (目標: {target_desc})"
        )

    def on_page_processed(self, stats: PageProcessStats) -> None:
        self.total_pages = stats.page
        self.total_skipped += stats.skipped_count

        target_str = f"/{stats.target_count}" if stats.target_count is not None else ""
        status_suffix = ""
        if stats.target_count is not None and stats.accumulated_new >= stats.target_count:
            status_suffix = " [bold green](達成目標)[/bold green]"

        self.console.print(
            f"  [bold white][頁 {stats.page}][/bold white] 探索 [bold cyan]{stats.total_in_page}[/bold cyan] 筆 "
            f"(新物件: [bold green]{stats.new_count}[/bold green] 筆, "
            f"已存在跳過: [dim yellow]{stats.skipped_count}[/dim yellow] 筆) "
            f"| 累計新入庫: [bold green]{stats.accumulated_new}{target_str}[/bold green] 筆{status_suffix}"
        )

    def on_item_fetching(self, title: str) -> None:
        pass

    def on_item_duplicate(self, title: str, matched_id: str) -> None:
        self.duplicates_count += 1
        clean_title = sanitize_terminal_text(title, max_len=20)
        self.console.print(
            f"    [bold magenta][去重合併][/bold magenta] -> [white]{clean_title}[/white] "
            f"歸戶至既有實體 [dim]{matched_id}[/dim]"
        )

    def on_interrupted(self, accumulated_count: int, domain_name: str) -> None:
        self.console.print(
            f"\n  [bold yellow][INFO] 接收到中斷訊號，{domain_name}同步作業提早安全退出。[/bold yellow]\n"
            f"  已安全提交入庫 [bold green]{accumulated_count}[/bold green] 筆實體。下次執行時將自動跳過已抓取物件。"
        )

    def on_domain_complete(self, summary_stats: Dict[str, Any]) -> None:
        total = summary_stats.get("total", 0)
        dups = summary_stats.get("duplicates", self.duplicates_count)
        details = summary_stats.get("details", total)
        skipped = summary_stats.get("skipped", self.total_skipped)
        pages = summary_stats.get("pages", self.total_pages)
        domain_name = summary_stats.get("domain", self.current_domain or "資料")

        unit_name = "筆刊登" if domain_name == "中古屋" else "筆實體"
        aggregation_info = f" (聚合為 [bold cyan]{total - dups}[/bold cyan] 戶客觀實體)" if dups > 0 else ""

        self.console.print(
            f"  [bold green][OK] {domain_name}領域同步完成！[/bold green] "
            f"共掃描 [bold white]{pages}[/bold white] 頁，"
            f"新入庫 [bold cyan]{total}[/bold cyan] {unit_name}{aggregation_info} "
            f"(跳過 [dim yellow]{skipped}[/dim yellow] 筆既有物件，"
            f"[bold magenta]{dups}[/bold magenta] 處刊登去重合併，"
            f"[bold yellow]{details}[/bold yellow] 筆豐富規格)"
        )

    def on_error(self, message: str) -> None:
        clean_msg = sanitize_terminal_text(message)
        self.console.print(f"    [bold red][警告]:[/bold red] {clean_msg}")
