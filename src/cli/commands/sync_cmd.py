"""HouseLensAPI CLI - 數據同步命令 (Sync Commands)

純淨架構：全面採用兩階段標準同步 (清單探索 + 併發詳情補齊 + 入庫消歧)，徹底移除過渡性 --details 旗標。
"""

import asyncio
from typing import Optional
import typer

from src.application.progress import RichProgressReporter, SilentProgressReporter
from src.application.sync_usecase import SyncUseCase
from src.cli.views.console import print_error, print_json_data, print_success
from src.domain.community import CommunitySearchQuery
from src.domain.new_house import NewHouseSearchQuery
from src.domain.sale_house import SaleHouseSearchQuery
from src.storage.database import db_manager

sync_app = typer.Typer(help="從外部房產平台兩階段同步資料並進行入庫與去重")


@sync_app.command("community")
def sync_communities_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="社區關鍵字"),
    min_age: Optional[float] = typer.Option(None, "--min-age", help="最小屋齡 (年)"),
    max_age: Optional[float] = typer.Option(None, "--max-age", help="最大屋齡 (年)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限 (留空則同步整頁)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """兩階段同步社區資料 (清單探索 + 併發詳情補齊規格)"""
    uc = SyncUseCase(database=db_manager)
    query = CommunitySearchQuery(
        region_id=region_id,
        keyword=keyword,
        min_age_years=min_age,
        max_age_years=max_age,
        page_size=limit or 20,
    )

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_communities(
                    provider_id=provider,
                    query=query,
                    max_items=limit,
                    concurrency=concurrency,
                    reporter=SilentProgressReporter(),
                )
            )
            print_json_data({"synced_communities_count": len(results), "provider": provider})
        else:
            with RichProgressReporter() as reporter:
                asyncio.run(
                    uc.sync_communities(
                        provider_id=provider,
                        query=query,
                        max_items=limit,
                        concurrency=concurrency,
                        reporter=reporter,
                    )
                )
    except Exception as e:
        print_error(f"社區同步失敗: {e}")
        raise typer.Exit(code=1)


@sync_app.command("sale")
def sync_sale_houses_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="房屋搜尋關鍵字"),
    min_price: Optional[int] = typer.Option(None, "--min-price", help="最低總價 (萬元)"),
    max_price: Optional[int] = typer.Option(None, "--max-price", help="最高總價 (萬元)"),
    min_age: Optional[float] = typer.Option(None, "--min-age", help="最小屋齡 (年)"),
    max_age: Optional[float] = typer.Option(None, "--max-age", help="最大屋齡 (年)"),
    rooms: Optional[int] = typer.Option(None, "--rooms", help="格局房數篩選"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限 (留空則同步整頁)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """兩階段同步中古屋物件 (清單探索 + 併發詳情補齊產權五大面積與去重消歧)"""
    uc = SyncUseCase(database=db_manager)
    query = SaleHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        min_price_wan=min_price,
        max_price_wan=max_price,
        min_age_years=min_age,
        max_age_years=max_age,
        rooms=rooms,
        page_size=limit or 20,
    )

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_sale_houses(
                    provider_id=provider,
                    query=query,
                    max_items=limit,
                    concurrency=concurrency,
                    reporter=SilentProgressReporter(),
                )
            )
            print_json_data({"synced_properties_count": len(results), "provider": provider})
        else:
            with RichProgressReporter() as reporter:
                asyncio.run(
                    uc.sync_sale_houses(
                        provider_id=provider,
                        query=query,
                        max_items=limit,
                        concurrency=concurrency,
                        reporter=reporter,
                    )
                )
    except Exception as e:
        print_error(f"中古屋同步失敗: {e}")
        raise typer.Exit(code=1)


@sync_app.command("newhouse")
def sync_new_houses_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="建案名稱關鍵字"),
    status: Optional[str] = typer.Option("1,2", "--status", "-s", help="建案狀態 (1: 預售屋, 2: 新成屋, 1,2: 全部)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """兩階段同步預售屋與新建案資料 (清單探索 + 併發詳情補齊 layout_v2 房型規劃)"""
    uc = SyncUseCase(database=db_manager)

    is_pre = "1" in status if status else True
    is_new = "2" in status if status else True

    query = NewHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        is_presale=is_pre,
        is_new_construction=is_new,
        page_size=limit or 20,
    )

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_new_houses(
                    provider_id=provider,
                    query=query,
                    max_items=limit,
                    concurrency=concurrency,
                    reporter=SilentProgressReporter(),
                )
            )
            print_json_data({"synced_new_houses_count": len(results), "provider": provider})
        else:
            with RichProgressReporter() as reporter:
                asyncio.run(
                    uc.sync_new_houses(
                        provider_id=provider,
                        query=query,
                        max_items=limit,
                        concurrency=concurrency,
                        reporter=reporter,
                    )
                )
    except Exception as e:
        print_error(f"新建案同步失敗: {e}")
        raise typer.Exit(code=1)


@sync_app.command("all")
def sync_all_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    limit: Optional[int] = typer.Option(10, "--limit", "-l", help="各領域同步筆數上限 (預設 10)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
):
    """一鍵兩階段同步指定行政區的社區、中古屋與新建案三大領域完整資料"""
    print_success(f"開始全域兩階段同步 (來源: {provider}, 縣市 ID: {region_id}, 併發: {concurrency})...")
    sync_communities_cmd(provider=provider, region_id=region_id, limit=limit, concurrency=concurrency, keyword=None, min_age=None, max_age=None, format_opt="text")
    sync_sale_houses_cmd(provider=provider, region_id=region_id, limit=limit, concurrency=concurrency, keyword=None, min_price=None, max_price=None, min_age=None, max_age=None, rooms=None, format_opt="text")
    sync_new_houses_cmd(provider=provider, region_id=region_id, limit=limit, concurrency=concurrency, keyword=None, status="1,2", format_opt="text")
    print_success("全域三大領域兩階段同步作業全部完成！")
