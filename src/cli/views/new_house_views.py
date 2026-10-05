"""HouseLensAPI - 新建案領域與 layout_v2 Rich 視圖渲染器 (New House Views)

純淨規範：以專業清晰之終端排版呈現，嚴禁使用裝飾性 emoji。
"""

from typing import Any, Dict, List
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from src.storage.models.new_house import NewHouseTable


def render_new_house_table(new_houses: List[NewHouseTable]) -> Table:
    """渲染新建案清單表格"""
    table = Table(
        title=f"新建案清單列表 (共 {len(new_houses)} 案)",
        box=box.ROUNDED,
        header_style="bold blue",
        show_lines=True,
    )

    table.add_column("建案外部 ID", style="bold yellow", justify="center")
    table.add_column("建案名稱", style="bold white")
    table.add_column("期程狀態", style="magenta", justify="center")
    table.add_column("行政區域", style="yellow")
    table.add_column("開價單價區間", justify="right", style="green")
    table.add_column("規劃坪數", justify="right")
    table.add_column("投資建設 / 營造", style="dim", max_width=30, overflow="ellipsis")
    table.add_column("接待會館/基地地址", style="dim", max_width=30, overflow="ellipsis")

    for nh in new_houses:
        specs_team = f"{nh.developer_company or '-'} / {nh.builder_company or '-'}"
        addr_str = nh.address or nh.reception_address or "-"

        # 單價區間
        if nh.min_unit_price_wan is not None and nh.max_unit_price_wan is not None:
            if nh.min_unit_price_wan == nh.max_unit_price_wan:
                price_str = f"{nh.min_unit_price_wan:.0f} 萬/坪"
            else:
                price_str = f"{nh.min_unit_price_wan:.0f}~{nh.max_unit_price_wan:.0f} 萬/坪"
        else:
            price_str = "-"

        # 坪數區間
        if nh.min_area_pin is not None and nh.max_area_pin is not None:
            if nh.min_area_pin == nh.max_area_pin:
                area_str = f"{nh.min_area_pin:.0f} 坪"
            else:
                area_str = f"{nh.min_area_pin:.0f}~{nh.max_area_pin:.0f} 坪"
        else:
            area_str = "-"

        table.add_row(
            f"[{nh.provider_id}] {nh.external_project_id}",
            nh.project_name,
            nh.build_type,
            f"{nh.region_name}{nh.section_name}",
            price_str,
            area_str,
            specs_team,
            addr_str,
        )

    return table


def render_new_house_detail_view(nh: NewHouseTable) -> Group:
    """渲染新建案規格面板與房型規劃矩陣"""
    specs_table = Table.grid(padding=(0, 2))
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")

    # 單價區間
    if nh.min_unit_price_wan is not None and nh.max_unit_price_wan is not None:
        if nh.min_unit_price_wan == nh.max_unit_price_wan:
            price_str = f"{nh.min_unit_price_wan:.0f} 萬/坪"
        else:
            price_str = f"{nh.min_unit_price_wan:.0f}~{nh.max_unit_price_wan:.0f} 萬/坪"
    else:
        price_str = "價格待定"

    # 坪數區間
    if nh.min_area_pin is not None and nh.max_area_pin is not None:
        if nh.min_area_pin == nh.max_area_pin:
            area_str = f"{nh.min_area_pin:.0f} 坪"
        else:
            area_str = f"{nh.min_area_pin:.0f}~{nh.max_area_pin:.0f} 坪"
    else:
        area_str = "-"

    base_str = f"{nh.base_area_pin:.2f} 坪" if nh.base_area_pin is not None else "-"
    pub_str = f"{nh.public_ratio_pct:.1f}%" if nh.public_ratio_pct is not None else "-"
    hh_str = f"{nh.total_households} 戶" if nh.total_households is not None else "-"
    mgmt_fee_str = f"{nh.manage_fee_per_pin} 元/坪/月" if nh.manage_fee_per_pin is not None else "-"

    specs_table.add_row("外部 ID:", nh.external_project_id, "來源平台:", f"[{nh.provider_id.upper()}]")
    specs_table.add_row("建案名稱:", f"[bold yellow]{nh.project_name}[/bold yellow]", "建案狀態:", nh.build_type)
    specs_table.add_row("基地地址:", nh.address, "接待會館:", nh.reception_address or "-")
    specs_table.add_row("開價區間:", f"[bold green]{price_str}[/bold green]", "行政區域:", f"{nh.region_name}{nh.section_name}")
    specs_table.add_row("坪數範圍:", area_str, "基地總坪:", base_str)
    specs_table.add_row("公設比率:", pub_str, "規劃總戶數:", hh_str)
    specs_table.add_row("管理費單價:", mgmt_fee_str, "座向規則:", nh.direction_rule or "-")
    specs_table.add_row("結構工法:", nh.structural_engine or "-", "投資建設:", nh.developer_company or "-")
    specs_table.add_row("營造公司:", nh.builder_company or "-", "建築設計:", nh.architect_company or "-")

    base_panel = Panel(
        specs_table,
        title=f"新建案基本規格 - {nh.project_name}",
        border_style="blue",
        box=box.ROUNDED,
    )

    # 2. 結構化房型坪數矩陣 Table
    layouts_table = Table(
        title="房型規劃與坪數配置矩陣",
        box=box.SIMPLE_HEAD,
        header_style="bold yellow",
    )
    layouts_table.add_column("房型名稱", style="bold cyan", justify="center")
    layouts_table.add_column("對應房數", style="magenta", justify="center")
    layouts_table.add_column("規劃坪數區間", style="bold white", justify="center")

    layout_items = nh.layouts or []
    if layout_items:
        for it in layout_items:
            r_name = it.get("room_name") or it.get("room", "-")
            r_cnt = it.get("rooms_count")
            r_cnt_s = f"{r_cnt}房" if r_cnt is not None else "-"
            min_a = it.get("min_area_pin")
            max_a = it.get("max_area_pin")
            if min_a is not None and max_a is not None:
                area_s = f"{min_a:.0f}~{max_a:.0f} 坪" if min_a != max_a else f"{min_a:.0f} 坪"
            else:
                area_s = it.get("area") or "-"

            layouts_table.add_row(r_name, r_cnt_s, area_s)
    else:
        layouts_table.add_row("暫無結構化房型資訊", "-", "-")

    return Group(base_panel, layouts_table)


def new_house_to_dict(nh: NewHouseTable) -> Dict[str, Any]:
    """將 NewHouseTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": nh.id,
        "provider_id": nh.provider_id,
        "external_project_id": nh.external_project_id,
        "project_name": nh.project_name,
        "build_type": nh.build_type,
        "region_name": nh.region_name,
        "section_name": nh.section_name,
        "address": nh.address,
        "min_unit_price_wan": nh.min_unit_price_wan,
        "max_unit_price_wan": nh.max_unit_price_wan,
        "min_area_pin": nh.min_area_pin,
        "max_area_pin": nh.max_area_pin,
        "base_area_pin": nh.base_area_pin,
        "public_ratio_pct": nh.public_ratio_pct,
        "total_households": nh.total_households,
        "manage_fee_per_pin": nh.manage_fee_per_pin,
        "layouts": nh.layouts,
        "structural_engine": nh.structural_engine,
        "direction_rule": nh.direction_rule,
        "developer_company": nh.developer_company,
        "builder_company": nh.builder_company,
        "architect_company": nh.architect_company,
        "reception_address": nh.reception_address,
        "cover_image_url": nh.cover_image_url,
        "updated_at": nh.updated_at.isoformat() if nh.updated_at else None,
    }
