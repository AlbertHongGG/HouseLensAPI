"""HouseLensAPI - 主 CLI 命令列進入點 (Main CLI Application Entry)"""

import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer

from src.cli.commands.db_cmd import db_app
from src.cli.commands.get_cmd import get_app
from src.cli.commands.list_cmd import list_app
from src.cli.commands.provider_cmd import provider_app
from src.cli.commands.sync_cmd import sync_app
from src.cli.views.console import print_error
from src.config import settings
from src.storage.database import db_manager

APP_VERSION = "0.1.0"

app = typer.Typer(
    name="houselens",
    help="HouseLens - 台灣全網房產數據終端管理系統 (Real Estate Terminal & CLI Engine)",
    no_args_is_help=True,
    add_completion=False,
)


# 掛載五大子命令群組
app.add_typer(provider_app, name="provider")
app.add_typer(db_app, name="db")
app.add_typer(sync_app, name="sync")
app.add_typer(list_app, name="list")
app.add_typer(get_app, name="get")


def version_callback(value: bool):
    if value:
        typer.echo(f"HouseLens CLI version {APP_VERSION}")
        raise typer.Exit()


@app.callback()
def main_callback(
    db_path: Optional[str] = typer.Option(
        None,
        "--db-path",
        envvar="HOUSELENS_DB_PATH",
        help="自訂 SQLite 資料庫路徑 (預設: ./houselens.db)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="開啟除錯模式，印出詳細 Exception Stacktrace",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="顯示目前 CLI 版本",
    ),
):
    """HouseLens 全域組態設定攔截器"""
    if debug:
        settings.debug = True

    if db_path:
        settings.db_path = db_path
        abs_path = Path(db_path).resolve().as_posix()
        db_manager.configure(f"sqlite+aiosqlite:///{abs_path}")


def cli_entry():
    """全域進入點包裝函式，攔截未預期崩潰"""
    try:
        app()
    except Exception as e:
        if settings.debug:
            raise
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli_entry()
