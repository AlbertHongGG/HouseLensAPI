"""HouseLensAPI CLI - 資料庫維護與指標命令 (Database Commands)"""

import asyncio
import typer

from src.application.db_usecase import DbMaintenanceUseCase
from src.cli.views.console import console, print_error, print_json_data, print_success
from src.cli.views.db_views import render_db_stats_dashboard
from src.storage.database import db_manager

db_app = typer.Typer(help="💾 本地資料庫維護、統計儀表板與重整")


@db_app.command("init")
def init_database():
    """初始化資料庫結構 (建立所有尚未存在之資料表)"""
    uc = DbMaintenanceUseCase(database=db_manager)
    try:
        asyncio.run(uc.init_db())
        print_success(f"資料庫結構初始化完成！位置: [bold cyan]{db_manager.db_url}[/bold cyan]")
    except Exception as e:
        print_error(f"資料庫初始化失敗: {e}")
        raise typer.Exit(code=1)


@db_app.command("stats")
def show_stats(
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """檢視資料庫健康指標、庫存容量與多平台消歧去重率儀表板"""
    uc = DbMaintenanceUseCase(database=db_manager)
    try:
        stats = asyncio.run(uc.get_stats())
    except Exception as e:
        print_error(f"取得資料庫統計失敗: {e}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        print_json_data(stats)
        return

    dashboard = render_db_stats_dashboard(stats)
    console.print(dashboard)


@db_app.command("vacuum")
def vacuum_database():
    """執行資料庫重整與空間最佳化回收 (VACUUM)"""
    uc = DbMaintenanceUseCase(database=db_manager)
    try:
        asyncio.run(uc.vacuum())
        print_success("資料庫重整 (VACUUM) 執行完成！")
    except Exception as e:
        print_error(f"資料庫重整失敗: {e}")
        raise typer.Exit(code=1)
