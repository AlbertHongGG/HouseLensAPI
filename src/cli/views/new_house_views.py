"""HouseLensAPI - 新建案領域與 layout_v2 Rich 視圖渲染器 (New House Views)"""

from typing import Any, Dict, List
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from src.storage.models.new_house import NewHouseTable


def render_new_house_table(new_houses: List[NewHouseTable]) -> Table:
    """渲染新建案清單表格"""
    table = Table(
        title=f"🏗️ 庫存新建案清單 (共 {len(new_houses)} 案)",
        box=box.ROUNDED,
        header_style="bold blue",
        show_lines=True,
    )

    table.add_column("建案 HID", style="bold yellow", justify="center")
    table.add_column("建案名稱", style="bold white")
    table.add_column("狀態", style="magenta", justify="center")
    table.add_column("行政區域", style="yellow")
    table.add_column("開價區間", justify="right", style="green")
    table.add_column("規劃坪數", justify="right")
    table.add_column("投資建設 / 營造", style="dim", max_width=30, overflow="ellipsis")
    table.add_column("接待會館/地址", style="dim", max_width=30, overflow="ellipsis")

    for nh in new_houses:
        specs_team = f"{nh.developer_company or '-'} / {nh.builder_company or '-'}"
        addr_str = nh.address or nh.reception_address or "-"

        table.add_row(
            str(nh.source_hid),
            nh.project_name,
            nh.build_type,
            f"{nh.region}{nh.section}",
            nh.price or nh.unit_price_str or "-",
            nh.area or "-",
            specs_team,
            addr_str,
        )

    return table


def render_new_house_detail_view(nh: NewHouseTable) -> Group:
    """渲染新建案規格面板與 layout_v2 房型規劃矩陣"""
    # 1. 建築規格 Table
    specs_table = Table.grid(padding=(0, 2))
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")

    specs_table.add_row("建案 HID:", str(nh.source_hid), "來源平台:", f"[{nh.provider_id.upper()}]")
    specs_table.add_row("建案名稱:", f"[bold yellow]{nh.project_name}[/bold yellow]", "建案狀態:", nh.build_type)
    specs_table.add_row("基地地址:", nh.address, "接待會館:", nh.reception_address or "-")
    specs_table.add_row("開價區間:", f"[bold green]{nh.price or nh.unit_price_str or '-'}[/bold green]", "車位開價:", nh.parking_price_str or "-")
    specs_table.add_row("坪數範圍:", nh.area or "-", "基地坪數:", f"{nh.base_area_ping or '-'} 坪")
    specs_table.add_row("公設比:", nh.public_ratio or "-", "總戶數:", nh.total_households or "-")
    specs_table.add_row("管理費:", nh.manage_cost or "-", "車位規劃:", nh.park_planning or "-")
    specs_table.add_row("車位配比:", nh.park_ratio or "-", "座向規則:", nh.direction_rule or "-")
    specs_table.add_row("結構工程:", nh.structural_engine or "-", "投資建設:", nh.developer_company or "-")
    specs_table.add_row("營造公司:", nh.builder_company or "-", "建築設計:", nh.architect_company or "-")

    intro_text = nh.build_intro or "暫無建案特色說明"
    specs_table.add_row("建材與特色:", f"[dim]{intro_text[:120]}...[/dim]" if len(intro_text) > 120 else intro_text, "", "")

    base_panel = Panel(
        specs_table,
        title=f"🏗️ 新建案基本規格 - {nh.project_name}",
        border_style="blue",
        box=box.ROUNDED,
    )

    # 2. 結構化 layout_v2 房型坪數矩陣 Table
    layouts_table = Table(
        title="📐 房型規劃與坪數配置矩陣 (layout_v2)",
        box=box.SIMPLE_HEAD,
        header_style="bold yellow",
    )
    layouts_table.add_column("規劃房型 (Room)", style="bold cyan", justify="center")
    layouts_table.add_column("坪數區間 (Area Ping)", style="bold white", justify="center")

    layout_items = nh.layout_v2 or []
    if layout_items:
        for it in layout_items:
            room = it.get("room", "-")
            area = it.get("area", "-")
            layouts_table.add_row(f"🛏️ {room}", f"📏 {area} 坪")
    else:
        layouts_table.add_row("暫無結構化房型資訊", "-")

    return Group(base_panel, layouts_table)


def new_house_to_dict(nh: NewHouseTable) -> Dict[str, Any]:
    """將 NewHouseTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": nh.id,
        "source_hid": nh.source_hid,
        "provider_id": nh.provider_id,
        "project_name": nh.project_name,
        "build_type": nh.build_type,
        "region": nh.region,
        "section": nh.section,
        "address": nh.address,
        "price": nh.price,
        "area": nh.area,
        "unit_price_str": nh.unit_price_str,
        "parking_price_str": nh.parking_price_str,
        "base_area_ping": nh.base_area_ping,
        "public_ratio": nh.public_ratio,
        "total_households": nh.total_households,
        "manage_cost": nh.manage_cost,
        "structural_engine": nh.structural_engine,
        "park_planning": nh.park_planning,
        "direction_rule": nh.direction_rule,
        "park_ratio": nh.park_ratio,
        "build_intro": nh.build_intro,
        "layout_v2": nh.layout_v2,
        "developer_company": nh.developer_company,
        "builder_company": nh.builder_company,
        "architect_company": nh.architect_company,
        "reception_address": nh.reception_address,
        "updated_at": nh.updated_at.isoformat() if nh.updated_at else None,
    }
