"""HouseLensAPI CLI - 中古屋社區關聯補齊與消歧命令 (Link Communities Command)

純淨架構：提供獨立維護指令，掃描資料庫中尚未關聯社區之中古屋，
進行記憶體 DISTINCT 去重聚合，透過本地對齊與遠端兩層式清單探索補齊社區並更新外鍵。
"""

import asyncio
from typing import Optional
import typer

from src.cli.views.console import console, print_error, print_json_data, print_success
from src.cli.views.link_views import (
    render_community_link_dashboard,
    render_community_link_details_table,
)
from src.services.community_resolver import (
    CommunityResolutionOptions,
    CommunityResolutionService,
)
from src.storage.database import db_manager


async def _run_link_communities(options: CommunityResolutionOptions, format_opt: str):
    await db_manager.init_db()
    service = CommunityResolutionService(database=db_manager)
    report = await service.resolve_unlinked_properties(options)

    if format_opt == "json":
        print_json_data(report.model_dump())
        return

    # 渲染終端儀表板
    dashboard = render_community_link_dashboard(report, is_dry_run=options.dry_run)
    console.print(dashboard)

    # 渲染詳細明細清單
    if report.details:
        table = render_community_link_details_table(report)
        console.print(table)


def link_communities_cmd(
    provider: str = typer.Option("591", "--provider", "-p", help="來源平台代碼 (預設 591)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="限定特定行政縣市 (如 台北市、新北市)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="掃描處理的中古屋筆數上限"),
    dry_run: bool = typer.Option(False, "--dry-run", help="乾跑預演模式 (僅分析比對與輸出報表，不寫入資料庫)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """掃描庫存未關聯社區之中古屋，聚合去重並透過兩階段消歧補齊社區實體與外鍵"""
    options = CommunityResolutionOptions(
        provider_id=provider,
        region_name=region,
        limit=limit,
        dry_run=dry_run,
    )
    asyncio.run(_run_link_communities(options, format_opt=format_opt))
