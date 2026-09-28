"""HouseLensAPI CLI - 數據同步命令 (Sync Commands)"""

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

sync_app = typer.Typer(help="🔄 從外部房產平台同步資料並進行入庫與去重")


@sync_app.command("community")
def sync_communities_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="社區關鍵字"),
    details: bool = typer.Option(False, "--details", "-d", help="是否深入爬取完整規格與公設詳情"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限 (留空則同步整頁)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """同步社區資料 (支援區域與關鍵字檢索)"""
    uc = SyncUseCase(database=db_manager)
    query = CommunitySearchQuery(region_id=region_id, keyword=keyword, page_size=limit or 20)

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_communities(
                    provider_id=provider,
                    query=query,
                    sync_details=details,
                    max_items=limit,
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
                        sync_details=details,
                        max_items=limit,
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
    details: bool = typer.Option(False, "--details", "-d", help="是否深入爬取產權面積拆解與建築規格詳情"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限 (留空則同步整頁)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """同步中古屋物件 (自動透過消歧服務進行去重並聚合跨平台刊登)"""
    uc = SyncUseCase(database=db_manager)
    query = SaleHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        min_price=min_price,
        max_price=max_price,
    )

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_sale_houses(
                    provider_id=provider,
                    query=query,
                    sync_details=details,
                    max_items=limit,
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
                        sync_details=details,
                        max_items=limit,
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
    status: Optional[str] = typer.Option("1,2", "--status", "-s", help="建案狀態 (1: 預售屋, 2: 新成屋)"),
    details: bool = typer.Option(False, "--details", "-d", help="是否深入爬取 layout_v2 房型規劃矩陣與建商團隊"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步筆數上限"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """同步預售屋與新建案資料 (含 layout_v2 結構化房型坪數)"""
    uc = SyncUseCase(database=db_manager)
    query = NewHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        build_status=status,
        page_size=limit or 20,
    )

    try:
        if format_opt == "json":
            results = asyncio.run(
                uc.sync_new_houses(
                    provider_id=provider,
                    query=query,
                    sync_details=details,
                    max_items=limit,
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
                        sync_details=details,
                        max_items=limit,
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
    details: bool = typer.Option(False, "--details", "-d", help="是否深入爬取詳情"),
    limit: Optional[int] = typer.Option(10, "--limit", "-l", help="各領域同步筆數上限 (預設 10)"),
):
    """一鍵同步指定行政區的社區、中古屋與新建案三大領域完整資料"""
    print_success(f"開始全域同步 (來源: {provider}, 縣市 ID: {region_id})...")
    sync_communities_cmd(provider=provider, region_id=region_id, details=details, limit=limit, keyword=None, format_opt="text")
    sync_sale_houses_cmd(provider=provider, region_id=region_id, details=details, limit=limit, keyword=None, min_price=None, max_price=None, format_opt="text")
    sync_new_houses_cmd(provider=provider, region_id=region_id, details=details, limit=limit, keyword=None, status="1,2", format_opt="text")
    print_success("全域三大領域同步作業全部完成！")
