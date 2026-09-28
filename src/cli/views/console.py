"""HouseLensAPI - CLI 終端輸出與 Console 管理 (Console & Message Views)"""

import json
import sys
from typing import Any
from rich.console import Console
from rich.theme import Theme

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "bold magenta",
})

console = Console(theme=custom_theme)
err_console = Console(theme=custom_theme, stderr=True)


def get_console() -> Console:
    """取得全域 Rich Console 實例"""
    return console


def print_success(message: str) -> None:
    """輸出成功訊息"""
    console.print(f"[success]✔[/success] {message}")


def print_error(message: str) -> None:
    """輸出錯誤訊息至 stderr"""
    err_console.print(f"[error]✘ 錯誤:[/error] {message}")


def print_warning(message: str) -> None:
    """輸出警告訊息"""
    console.print(f"[warning]! 警告:[/warning] {message}")


def print_info(message: str) -> None:
    """輸出提示訊息"""
    console.print(f"[info]ℹ[/info] {message}")


def print_json_data(data: Any) -> None:
    """輸出格式化 JSON 資料 (適用於 --format json 管線)"""
    if isinstance(data, (dict, list)):
        raw = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        raw = str(data)
    console.print(raw, soft_wrap=True)
