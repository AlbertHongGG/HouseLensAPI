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
    table.add_column("狀態/型態", style="magenta", justify="center")
    table.add_column("行政區域", style="yellow")
    table.add_column("開價單價區間", justify="right", style="green")
    table.add_column("規劃坪數", justify="right")
    table.add_column("完工/交屋期程", style="cyan", justify="center")
    table.add_column("投資建設 / 營造", style="dim", max_width=25, overflow="ellipsis")
    table.add_column("基地地址", style="dim", max_width=25, overflow="ellipsis")

    for nh in new_houses:
        specs_team = f"{nh.developer_company or '-'} / {nh.builder_company or '-'}"
        addr_str = nh.address or nh.reception_address or "-"
        b_type_str = f"{nh.build_type or '-'}"
        if nh.building_type:
            b_type_str += f" ({nh.building_type})"

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
            b_type_str,
            f"{nh.region_name}{nh.section_name}",
            price_str,
            area_str,
            nh.handover_time or "-",
            specs_team,
            addr_str,
        )

    return table


def render_new_house_detail_view(nh: NewHouseTable) -> Group:
    """渲染新建案規格面板、車位規格、建築團隊與房型規劃矩陣"""
    # 1. 基本規格與時程用途表格
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
    specs_table.add_row("建案名稱:", f"[bold yellow]{nh.project_name}[/bold yellow]", "期程狀態:", nh.build_type)
    specs_table.add_row("建物型態:", nh.building_type or "-", "法定用途:", nh.legal_purpose or "-")
    specs_table.add_row("土地分區:", nh.land_division or "-", "行政區域:", f"{nh.region_name}{nh.section_name}")
    specs_table.add_row("基地地址:", nh.address, "接待會館:", nh.reception_address or "-")
    specs_table.add_row("完工期程:", nh.handover_time or "-", "公開銷售:", nh.open_sell_date or "-")
    specs_table.add_row("開價區間:", f"[bold green]{price_str}[/bold green]", "坪數範圍:", area_str)
    specs_table.add_row("基地總坪:", base_str, "公設比率:", pub_str)
    specs_table.add_row("規劃總戶數:", hh_str, "管理費單價:", mgmt_fee_str)
    specs_table.add_row("結構工法:", nh.structural_engine or "-", "座向規則:", nh.direction_rule or "-")

    base_panel = Panel(
        specs_table,
        title=f"新建案基本規格 - {nh.project_name}",
        border_style="blue",
        box=box.ROUNDED,
    )

    # 2. 車位規格與充電設備表格
    park_table = Table.grid(padding=(0, 2))
    park_table.add_column(style="bold cyan", justify="right")
    park_table.add_column(style="white")
    park_table.add_column(style="bold cyan", justify="right")
    park_table.add_column(style="white")

    p_price_s = nh.parking_price_desc or "-"
    if nh.min_parking_price_wan is not None and nh.max_parking_price_wan is not None:
        if nh.min_parking_price_wan == nh.max_parking_price_wan:
            p_price_s = f"{nh.min_parking_price_wan:.0f} 萬"
        else:
            p_price_s = f"{nh.min_parking_price_wan:.0f}~{nh.max_parking_price_wan:.0f} 萬"

    p_counts = []
    if nh.plane_parking_count is not None:
        p_counts.append(f"平面 {nh.plane_parking_count} 個")
    if nh.mechanical_parking_count is not None:
        p_counts.append(f"機械 {nh.mechanical_parking_count} 個")
    p_cnt_str = "、".join(p_counts) if p_counts else (nh.parking_planning_desc or "-")

    charging_s = nh.charging_piles_desc or ("有" if nh.has_charging_piles else "-")

    park_table.add_row("車位價格:", p_price_s, "車位配比:", nh.parking_ratio_desc or "-")
    park_table.add_row("車位規劃:", p_cnt_str, "車位風格:", nh.parking_style or "標準地下室/暫無")
    park_table.add_row("充電設備:", charging_s, "預留充電樁:", "是" if nh.has_charging_piles else "否")

    park_panel = Panel(
        park_table,
        title="車位規劃與充電設備規格",
        border_style="green",
        box=box.ROUNDED,
    )

    # 3. 建築團隊、代銷、關聯社區與地理坐標
    team_table = Table.grid(padding=(0, 2))
    team_table.add_column(style="bold cyan", justify="right")
    team_table.add_column(style="white")
    team_table.add_column(style="bold cyan", justify="right")
    team_table.add_column(style="white")

    coord_s = f"{nh.latitude:.5f}, {nh.longitude:.5f}" if nh.latitude and nh.longitude else "-"
    comm_s = f"{nh.community_name or '-'} (ID: {nh.external_community_id or '-'})"

    team_table.add_row("投資建設:", nh.developer_company or "-", "營造公司:", nh.builder_company or "-")
    team_table.add_row("建築設計:", nh.architect_company or "-", "企劃銷售:", nh.sales_agency_company or "-")
    team_table.add_row("關聯社區:", comm_s, "社區屋齡:", f"{nh.community_age} 年" if nh.community_age is not None else "-")
    team_table.add_row("基地經緯度:", coord_s, "", "")

    team_panel = Panel(
        team_table,
        title="專業團隊、企劃代理與關聯社區",
        border_style="magenta",
        box=box.ROUNDED,
    )

    # 4. 結構化房型坪數矩陣 Table
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

    return Group(base_panel, park_panel, team_panel, layouts_table)


def new_house_to_dict(nh: NewHouseTable) -> Dict[str, Any]:
    """將 NewHouseTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": nh.id,
        "provider_id": nh.provider_id,
        "external_project_id": nh.external_project_id,
        "project_name": nh.project_name,
        "build_type": nh.build_type,
        "building_type": nh.building_type,
        "legal_purpose": nh.legal_purpose,
        "land_division": nh.land_division,
        "region_name": nh.region_name,
        "section_name": nh.section_name,
        "address": nh.address,
        "handover_time": nh.handover_time,
        "open_sell_date": nh.open_sell_date,
        "min_unit_price_wan": nh.min_unit_price_wan,
        "max_unit_price_wan": nh.max_unit_price_wan,
        "min_area_pin": nh.min_area_pin,
        "max_area_pin": nh.max_area_pin,
        "base_area_pin": nh.base_area_pin,
        "public_ratio_pct": nh.public_ratio_pct,
        "total_households": nh.total_households,
        "manage_fee_per_pin": nh.manage_fee_per_pin,
        "parking": {
            "min_parking_price_wan": nh.min_parking_price_wan,
            "max_parking_price_wan": nh.max_parking_price_wan,
            "parking_price_desc": nh.parking_price_desc,
            "parking_ratio_desc": nh.parking_ratio_desc,
            "parking_ratio_val": nh.parking_ratio_val,
            "parking_planning_desc": nh.parking_planning_desc,
            "plane_parking_count": nh.plane_parking_count,
            "mechanical_parking_count": nh.mechanical_parking_count,
            "charging_piles_desc": nh.charging_piles_desc,
            "has_charging_piles": nh.has_charging_piles,
            "parking_style": nh.parking_style,
        },
        "layouts": nh.layouts,
        "structural_engine": nh.structural_engine,
        "direction_rule": nh.direction_rule,
        "developer_company": nh.developer_company,
        "builder_company": nh.builder_company,
        "architect_company": nh.architect_company,
        "sales_agency_company": nh.sales_agency_company,
        "reception_address": nh.reception_address,
        "external_community_id": nh.external_community_id,
        "community_name": nh.community_name,
        "community_age": nh.community_age,
        "latitude": nh.latitude,
        "longitude": nh.longitude,
        "cover_image_url": nh.cover_image_url,
        "updated_at": nh.updated_at.isoformat() if nh.updated_at else None,
    }
