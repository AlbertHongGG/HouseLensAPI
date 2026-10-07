"""HouseLensAPI CLI - 物件深度規格與比價檢視命令 (Get Commands)"""

import asyncio
from typing import Optional
import typer

from src.application.inspect_usecase import InspectUseCase
from src.cli.views.community_views import (
    community_to_dict,
    render_community_detail_panel,
)
from src.cli.views.console import console, print_error, print_json_data, print_warning
from src.cli.views.new_house_views import (
    new_house_to_dict,
    render_new_house_detail_view,
)
from src.cli.views.property_views import (
    property_to_dict,
    render_property_detail_view,
)
from src.storage.database import db_manager

get_app = typer.Typer(help="檢視單一房產物件深度規格與跨平台比價卡片")


@get_app.command("community")
def get_community_cmd(
    identifier: str = typer.Argument(..., help="社區內部 UUID 或外部平台社區代碼 (如 5855864 或 43035)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="來源平台代碼 (如 591, yungching)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """檢視社區完整建築規劃、公設清單、管理費與周邊交通"""
    uc = InspectUseCase(database=db_manager)

    async def _execute():
        await db_manager.init_db()
        comm = await uc.get_community(identifier, provider_id=provider)
        if not comm and provider:
            try:
                comm = await uc.fetch_and_save_community(provider, identifier)
            except Exception:
                pass
        return comm

    try:
        community = asyncio.run(_execute())
    except Exception as e:
        print_error(f"查詢社區失敗: {e}")
        raise typer.Exit(code=1)

    if not community:
        print_warning(f"在本地資料庫找不到社區代號 '{identifier}'。")
        raise typer.Exit(code=1)

    if format_opt == "json":
        print_json_data(community_to_dict(community))
    else:
        panel = render_community_detail_panel(community)
        console.print(panel)


@get_app.command("sale")
def get_sale_house_cmd(
    identifier: str = typer.Argument(..., help="房屋實體 UUID 或外部房源編號 (如 S20604856 或 Yungching GUID)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="來源平台代碼 (如 591, yungching)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """檢視中古屋客觀實體物理規格與跨平台刊登比價追蹤清單"""
    uc = InspectUseCase(database=db_manager)

    async def _execute():
        await db_manager.init_db()
        prop = await uc.get_property(identifier, provider_id=provider)
        if not prop and provider:
            try:
                prop = await uc.fetch_and_save_property(provider, identifier)
            except Exception:
                pass
        return prop

    try:
        property_obj = asyncio.run(_execute())
    except Exception as e:
        print_error(f"查詢房屋失敗: {e}")
        raise typer.Exit(code=1)

    if not property_obj:
        print_warning(f"在本地資料庫找不到房屋實體或刊登編號 '{identifier}'。")
        raise typer.Exit(code=1)

    if format_opt == "json":
        print_json_data(property_to_dict(property_obj))
    else:
        view = render_property_detail_view(property_obj)
        console.print(view)


@get_app.command("newhouse")
def get_new_house_cmd(
    identifier: str = typer.Argument(..., help="建案內部 UUID 或建案 HID (如 138045)"),
    format_opt: str = typer.Option("text", "--format", "-f", help="輸出格式: text 或 json"),
):
    """檢視新建案建材特色、建築團隊與 layout_v2 房型坪數規劃矩陣"""
    uc = InspectUseCase(database=db_manager)
    try:
        new_house = asyncio.run(uc.get_new_house(identifier))
    except Exception as e:
        print_error(f"查詢新建案失敗: {e}")
        raise typer.Exit(code=1)

    if not new_house:
        print_warning(f"在本地資料庫找不到新建案編號 '{identifier}'。")
        raise typer.Exit(code=1)

    if format_opt == "json":
        print_json_data(new_house_to_dict(new_house))
    else:
        view = render_new_house_detail_view(new_house)
        console.print(view)
