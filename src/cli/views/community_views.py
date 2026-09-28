"""HouseLensAPI - 社區領域 Rich 視圖渲染器 (Community Views)"""

from typing import Any, Dict, List
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.storage.models.community import CommunityTable


def render_community_table(communities: List[CommunityTable]) -> Table:
    """渲染社區清單表格"""
    table = Table(
        title=f"🏢 庫存社區清單 (共 {len(communities)} 筆)",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("內部 ID", style="dim", max_width=10, overflow="ellipsis")
    table.add_column("來源/外部 ID", style="magenta", justify="center")
    table.add_column("社區名稱", style="bold white")
    table.add_column("區域", style="yellow")
    table.add_column("類型", style="green")
    table.add_column("平均單價", justify="right", style="bold yellow")
    table.add_column("屋齡/戶數", justify="center")
    table.add_column("生活圈/捷運", style="dim")

    for c in communities:
        source_tag = f"[{c.source_provider}] {c.source_id}"
        region = f"{c.region_name or ''}{c.section_name or ''}"
        price_str = f"{c.avg_unit_price} {c.unit_price_unit or '萬/坪'}" if c.avg_unit_price else "-"
        specs = f"{c.age or '-'} / {c.total_households or '-'}"
        trans = f"{c.shopping_district or ''} {c.transport or ''}".strip() or "-"

        table.add_row(
            c.id[:8] + "...",
            source_tag,
            c.name,
            region,
            c.build_type or c.build_purpose or "-",
            price_str,
            specs,
            trans,
        )

    return table


def render_community_detail_panel(c: CommunityTable) -> Panel:
    """渲染單一社區詳情規格面板"""
    details_table = Table.grid(padding=(0, 2))
    details_table.add_column(style="bold cyan", justify="right")
    details_table.add_column(style="white")
    details_table.add_column(style="bold cyan", justify="right")
    details_table.add_column(style="white")

    price_str = f"{c.avg_unit_price} {c.unit_price_unit or '萬/坪'}" if c.avg_unit_price else "無報價"
    coords_str = f"({c.lat:.5f}, {c.lng:.5f})" if c.lat and c.lng else "-"

    details_table.add_row("社區 ID:", c.id, "外部來源:", f"{c.source_provider} ({c.source_id})")
    details_table.add_row("社區名稱:", f"[bold yellow]{c.name}[/bold yellow]", "均價行情:", price_str)
    details_table.add_row("地址描述:", c.address or "-", "地理座標:", coords_str)
    details_table.add_row("行政區域:", f"{c.region_name or ''} {c.section_name or ''}", "生活圈/捷運:", f"{c.shopping_district or '-'} / {c.transport or '-'}")
    details_table.add_row("建物型態:", c.build_type or "-", "法定用途:", c.build_purpose or "-")
    details_table.add_row("屋齡規格:", c.age or "-", "總戶數:", c.total_households or "-")
    details_table.add_row("樓層規劃:", c.floor_plan or "-", "建築結構:", c.structure or "-")
    details_table.add_row("基地坪數:", c.base_area_ping or "-", "公設比:", c.public_ratio or "-")
    details_table.add_row("車位數量:", c.parking_count or "-", "車位配比/型態:", f"{c.park_rate or '-'} ({c.park_type_str or '-'})")
    details_table.add_row("座向規則:", c.direction_rule or "-", "管理費:", c.management_fee or "-")
    details_table.add_row("投資建設:", c.developer_company or "-", "營造廠:", c.builder_company or "-")
    details_table.add_row("建築設計:", c.architect_company or "-", "景觀/公設設計:", f"{c.landscape_name or '-'} / {c.postulate_name or '-'}")

    # 公設清單
    facility_str = "、".join(c.facilities) if c.facilities else "無公設資料"
    details_table.add_row("公設項目:", facility_str, "", "")

    intro = c.build_intro or "暫無建案特色簡介"
    content = f"[bold green]基本規格與團隊[/bold green]\n"
    content_panel = Panel(
        details_table,
        title=f"🏢 社區詳情 - {c.name}",
        border_style="cyan",
        box=box.ROUNDED,
    )
    return content_panel


def community_to_dict(c: CommunityTable) -> Dict[str, Any]:
    """將 CommunityTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": c.id,
        "source_provider": c.source_provider,
        "source_id": c.source_id,
        "name": c.name,
        "region_name": c.region_name,
        "section_name": c.section_name,
        "address": c.address,
        "lat": c.lat,
        "lng": c.lng,
        "avg_unit_price": c.avg_unit_price,
        "unit_price_unit": c.unit_price_unit,
        "shopping_district": c.shopping_district,
        "transport": c.transport,
        "age": c.age,
        "total_households": c.total_households,
        "floor_plan": c.floor_plan,
        "structure": c.structure,
        "base_area_ping": c.base_area_ping,
        "public_ratio": c.public_ratio,
        "parking_count": c.parking_count,
        "park_rate": c.park_rate,
        "park_type_str": c.park_type_str,
        "direction_rule": c.direction_rule,
        "build_intro": c.build_intro,
        "facilities": c.facilities,
        "developer_company": c.developer_company,
        "builder_company": c.builder_company,
        "architect_company": c.architect_company,
        "management_fee": c.management_fee,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
