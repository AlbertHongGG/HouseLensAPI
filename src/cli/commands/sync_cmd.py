"""HouseLensAPI CLI - 數據同步命令 (Sync Commands)

純淨架構：全面採用標準三階段同步流水線 (分頁清單探索 + 併發詳情補齊 + 消歧入庫)，
支援目標筆數跨頁累加 (-l) 與全量同步模式。
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

sync_app = typer.Typer(help="從外部房產平台三階段同步資料並進行入庫與去重")


@sync_app.command("community")
def sync_communities_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼"),
    region_id: int = typer.Option(1, "--region-id", "-r", help="縣市代碼 (1: 台北市...)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="社區關鍵字"),
    min_age: Optional[float] = typer.Option(None, "--min-age", help="最小屋齡 (年)"),
    max_age: Optional[float] = typer.Option(None, "--max-age", help="最大屋齡 (年)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步目標筆數 (留空則全量同步)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """三階段同步社區資料 (分頁探索 + 併發詳情補齊 + 入庫)"""
    uc = SyncUseCase(database=db_manager)
    page_size = min(limit, 20) if limit and limit < 20 else 20
    query = CommunitySearchQuery(
        region_id=region_id,
        keyword=keyword,
        min_age_years=min_age,
        max_age_years=max_age,
        page_size=page_size,
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
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步目標筆數 (留空則全量同步)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """三階段同步中古屋物件 (分頁探索 + 併發詳情補齊產權五大面積與去重消歧)"""
    uc = SyncUseCase(database=db_manager)
    page_size = min(limit, 20) if limit and limit < 20 else 20
    query = SaleHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        min_price_wan=min_price,
        max_price_wan=max_price,
        min_age_years=min_age,
        max_age_years=max_age,
        page_size=page_size,
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
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="同步目標筆數 (留空則全量同步)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """三階段同步預售屋與新建案資料 (分頁探索 + 併發詳情補齊 layout_v2 房型規劃)"""
    uc = SyncUseCase(database=db_manager)

    is_pre = "1" in status if status else True
    is_new = "2" in status if status else True
    page_size = min(limit, 20) if limit and limit < 20 else 20

    query = NewHouseSearchQuery(
        region_id=region_id,
        keywords=keyword,
        is_presale=is_pre,
        is_new_construction=is_new,
        page_size=page_size,
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
    limit: Optional[int] = typer.Option(10, "--limit", "-l", help="各領域同步目標筆數 (預設 10, 留空為全量)"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="併發詳情補齊請求數 (預設 3)"),
):
    """一鍵三階段同步指定行政區的社區、中古屋與新建案三大領域完整資料"""
    uc = SyncUseCase(database=db_manager)
    print_success(f"啟動全域三大領域三階段同步作業 (來源: {provider}, 縣市 ID: {region_id}, 目標各領域: {limit or '全量'} 筆, 併發: {concurrency})")

    page_size = min(limit, 20) if limit and limit < 20 else 20
    reporter = RichProgressReporter()

    try:
        # 1. 社區領域同步
        comm_query = CommunitySearchQuery(region_id=region_id, page_size=page_size)
        asyncio.run(
            uc.sync_communities(
                provider_id=provider,
                query=comm_query,
                max_items=limit,
                concurrency=concurrency,
                reporter=reporter,
                domain_step=1,
                domain_total=3,
            )
        )

        # 2. 中古屋領域同步
        sale_query = SaleHouseSearchQuery(region_id=region_id, page_size=page_size)
        asyncio.run(
            uc.sync_sale_houses(
                provider_id=provider,
                query=sale_query,
                max_items=limit,
                concurrency=concurrency,
                reporter=reporter,
                domain_step=2,
                domain_total=3,
            )
        )

        # 3. 新建案領域同步
        new_query = NewHouseSearchQuery(
            region_id=region_id,
            is_presale=True,
            is_new_construction=True,
            page_size=page_size,
        )
        asyncio.run(
            uc.sync_new_houses(
                provider_id=provider,
                query=new_query,
                max_items=limit,
                concurrency=concurrency,
                reporter=reporter,
                domain_step=3,
                domain_total=3,
            )
        )

        print_success("全域三大領域串流同步作業全部順利完成！")
    except KeyboardInterrupt:
        print_success("同步作業已由使用者手動終止，已處理頁面已安全儲存。")
        raise typer.Exit(code=0)
    except Exception as e:
        print_error(f"全域同步作業遭遇非預期錯誤中止: {e}")
        raise typer.Exit(code=1)
