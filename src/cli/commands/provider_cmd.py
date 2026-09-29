"""HouseLensAPI CLI - 來源外掛模組管理命令 (Provider Commands)"""

import asyncio
import time
import typer
from rich import box
from rich.table import Table

from src.cli.views.console import console, print_error, print_json_data, print_success
from src.config import settings
from src.core.registry import registry
import src.providers  # 載入內建 providers

provider_app = typer.Typer(help="來源外掛模組管理與即時健康狀態檢查")


@provider_app.command("list")
def list_providers(
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """列出目前已安裝並註冊的所有來源外掛模組"""
    provider_ids = registry.list_providers()
    providers_info = []
    for pid in provider_ids:
        prov = registry.get_provider(pid)
        is_def = (pid == settings.default_provider)
        aliases = [a for a, target in registry._aliases.items() if target == pid]
        providers_info.append({
            "provider_id": prov.provider_id,
            "provider_name": prov.provider_name,
            "is_default": is_def,
            "aliases": aliases,
        })

    if format_opt == "json":
        print_json_data(providers_info)
        return

    table = Table(
        title=f"已註冊房產來源外掛模組 (共 {len(providers_info)} 個)",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("外掛代碼 (ID)", style="bold yellow")
    table.add_column("外掛顯示名稱", style="bold white")
    table.add_column("預設提供者", justify="center")
    table.add_column("別名 (Aliases)", style="dim")
    table.add_column("支援領域模組", style="green")

    for p in providers_info:
        default_badge = "[bold green]是[/bold green]" if p.get("is_default") else "[dim]否[/dim]"
        aliases_str = ", ".join(p.get("aliases", [])) or "-"
        table.add_row(
            p["provider_id"],
            p["provider_name"],
            default_badge,
            aliases_str,
            "社區 (Community)、中古屋 (SaleHouse)、新建案 (NewHouse)",
        )

    console.print(table)


@provider_app.command("check")
def check_provider(
    provider_id: str = typer.Argument("591", help="外掛代碼，如 591"),
):
    """執行即時連線健康檢查並量測延遲"""
    try:
        prov = registry.get_provider(provider_id)
    except Exception as e:
        print_error(f"找不到外掛模組 '{provider_id}': {e}")
        raise typer.Exit(code=1)

    console.print(f"正在對外掛 [bold cyan]{prov.provider_name}[/bold cyan] ({provider_id}) 發送健康檢查...")

    start_time = time.perf_counter()
    try:
        is_healthy = asyncio.run(prov.health_check())
        latency_ms = (time.perf_counter() - start_time) * 1000.0
    except Exception as e:
        print_error(f"健康檢查失敗: {e}")
        raise typer.Exit(code=1)

    if is_healthy:
        print_success(
            f"來源外掛 [bold cyan]{prov.provider_name}[/bold cyan] 連線正常！"
            f" 延遲: [bold green]{latency_ms:.1f} ms[/bold green]"
        )
    else:
        print_error(f"來源外掛 [bold cyan]{prov.provider_name}[/bold cyan] 回報異常狀態")
        raise typer.Exit(code=1)
