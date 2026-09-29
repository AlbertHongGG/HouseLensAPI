"""HouseLensAPI CLI - 本地庫存檢索命令 (List Commands)"""

import asyncio
from typing import Optional
import typer

from src.application.query_usecase import QueryUseCase
from src.cli.views.community_views import community_to_dict, render_community_table
from src.cli.views.console import console, print_error, print_json_data, print_warning
from src.cli.views.new_house_views import new_house_to_dict, render_new_house_table
from src.cli.views.property_views import property_to_dict, render_property_table
from src.storage.database import db_manager

list_app = typer.Typer(help="檢索本地資料庫庫存房產資料 (支援表格與 JSON 輸出)")


@list_app.command("community")
def list_communities_cmd(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="縣市篩選 (例如: 台北市)"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="行政區篩選 (例如: 松山區)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="關鍵字比對"),
    min_age: Optional[float] = typer.Option(None, "--min-age", help="最小屋齡 (年)"),
    max_age: Optional[float] = typer.Option(None, "--max-age", help="最大屋齡 (年)"),
    limit: int = typer.Option(20, "--limit", "-l", help="每頁筆數上限"),
    offset: int = typer.Option(0, "--offset", help="分頁偏移量"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """查詢在庫社區節點"""
    uc = QueryUseCase(database=db_manager)
    try:
        communities = asyncio.run(
            uc.list_communities(
                region=region,
                section=section,
                keyword=keyword,
                min_age=min_age,
                max_age=max_age,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        print_error(f"檢索社區失敗: {e}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [community_to_dict(c) for c in communities]
        print_json_data(data)
        return

    if not communities:
        print_warning("查無符合條件之在庫社區。請先執行 'houselens sync community' 同步資料！")
        return

    table = render_community_table(communities)
    console.print(table)


@list_app.command("sale")
def list_sale_houses_cmd(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="縣市篩選 (例如: 台北市)"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="行政區篩選 (例如: 松山區)"),
    min_price: Optional[int] = typer.Option(None, "--min-price", help="最低總價 (萬元)"),
    max_price: Optional[int] = typer.Option(None, "--max-price", help="最高總價 (萬元)"),
    min_age: Optional[float] = typer.Option(None, "--min-age", help="最小屋齡 (年)"),
    max_age: Optional[float] = typer.Option(None, "--max-age", help="最大屋齡 (年)"),
    rooms: Optional[int] = typer.Option(None, "--rooms", help="格局房數篩選"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="物件標題或社區關鍵字"),
    limit: int = typer.Option(20, "--limit", "-l", help="每頁筆數上限"),
    offset: int = typer.Option(0, "--offset", help="分頁偏移量"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """查詢在庫中古屋實體 (含各平台刊登筆數與比價聚合標記)"""
    uc = QueryUseCase(database=db_manager)
    try:
        properties = asyncio.run(
            uc.list_properties(
                region=region,
                section=section,
                keyword=keyword,
                min_price=min_price,
                max_price=max_price,
                min_age=min_age,
                max_age=max_age,
                rooms=rooms,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        print_error(f"檢索中古屋失敗: {e}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [property_to_dict(p) for p in properties]
        print_json_data(data)
        return

    if not properties:
        print_warning("查無符合條件之在庫中古屋。請先執行 'houselens sync sale' 同步資料！")
        return

    table = render_property_table(properties)
    console.print(table)


@list_app.command("newhouse")
def list_new_houses_cmd(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="縣市篩選 (例如: 台北市)"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="行政區篩選 (例如: 萬華區)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="建案名稱關鍵字"),
    limit: int = typer.Option(20, "--limit", "-l", help="每頁筆數上限"),
    offset: int = typer.Option(0, "--offset", help="分頁偏移量"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """查詢在庫新建案"""
    uc = QueryUseCase(database=db_manager)
    try:
        new_houses = asyncio.run(
            uc.list_new_houses(
                region=region,
                section=section,
                keyword=keyword,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        print_error(f"檢索新建案失敗: {e}")
        raise typer.Exit(code=1)

    if format_opt == "json":
        data = [new_house_to_dict(nh) for nh in new_houses]
        print_json_data(data)
        return

    if not new_houses:
        print_warning("查無符合條件之在庫新建案。請先執行 'houselens sync newhouse' 同步資料！")
        return

    table = render_new_house_table(new_houses)
    console.print(table)
