"""HouseLensAPI - 社區領域 Rich 視圖渲染器 (Community Views)

純淨規範：以專業清晰之終端排版呈現，嚴禁使用裝飾性 emoji。
"""

from typing import Any, Dict, List
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.storage.models.community import CommunityTable


def render_community_table(communities: List[CommunityTable]) -> Table:
    """渲染社區清單表格"""
    table = Table(
        title=f"社區實體列表 (共 {len(communities)} 筆)",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("內部 ID", style="dim", max_width=10, overflow="ellipsis")
    table.add_column("來源平台/ID", style="magenta", justify="center")
    table.add_column("社區名稱", style="bold white")
    table.add_column("區域", style="yellow")
    table.add_column("狀態", style="cyan", justify="center")
    table.add_column("型態", style="green")
    table.add_column("平均單價", justify="right", style="bold yellow")
    table.add_column("屋齡 / 戶數", justify="center")
    table.add_column("生活圈 / 捷運", style="dim")

    for c in communities:
        source_tag = f"[{c.source_provider}] {c.source_id}"
        region = f"{c.region_name or ''}{c.section_name or ''}"
        price_str = f"{c.avg_unit_price_wan:.1f} 萬/坪" if c.avg_unit_price_wan is not None else "-"

        age_s = f"{c.building_age_years:.1f}年" if c.building_age_years is not None else "-"
        hh_s = f"{c.total_households}戶" if c.total_households is not None else "-"
        specs = f"{age_s} / {hh_s}"

        trans = f"{c.shopping_district or ''} {c.transport or ''}".strip() or "-"

        table.add_row(
            c.id[:8] + "...",
            source_tag,
            c.name,
            region,
            c.housing_status or "-",
            c.building_type or "-",
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

    price_str = f"{c.avg_unit_price_wan:.1f} 萬/坪" if c.avg_unit_price_wan is not None else "無報價"
    coords_str = f"({c.lat:.5f}, {c.lng:.5f})" if c.lat and c.lng else "-"
    age_str = f"{c.building_age_years:.1f} 年" if c.building_age_years is not None else "-"
    hh_str = f"{c.total_households} 戶" if c.total_households is not None else "-"
    base_str = f"{c.base_area_pin:.2f} 坪" if c.base_area_pin is not None else "-"
    pub_str = f"{c.public_ratio_pct:.1f}%" if c.public_ratio_pct is not None else "-"
    park_cnt_str = f"{c.parking_count} 個" if c.parking_count is not None else "-"
    park_pct_str = f"{c.parking_ratio_pct:.1f}%" if c.parking_ratio_pct is not None else "-"
    mgmt_fee_str = f"{c.manage_fee_per_pin} 元/坪/月" if c.manage_fee_per_pin is not None else "-"

    details_table.add_row("社區 ID:", c.id, "外部來源:", f"{c.source_provider} ({c.source_id})")
    details_table.add_row("社區名稱:", f"[bold yellow]{c.name}[/bold yellow]", "均價行情:", price_str)
    details_table.add_row("地址描述:", c.address or "-", "地理座標:", coords_str)
    details_table.add_row("行政區域:", f"{c.region_name or ''} {c.section_name or ''}", "生活圈/捷運:", f"{c.shopping_district or '-'} / {c.transport or '-'}")
    details_table.add_row("狀態/型態:", f"{c.housing_status or '-'} / {c.building_type or '-'}", "法定用途:", c.build_purpose or "-")
    details_table.add_row("屋齡規格:", age_str, "規劃總戶數:", hh_str)
    details_table.add_row("樓層規劃:", c.floor_plan or "-", "建築結構:", c.structure or "-")
    details_table.add_row("基地總坪:", base_str, "公設比率:", pub_str)
    details_table.add_row("車位總數:", park_cnt_str, "車位配比/型態:", f"{park_pct_str} ({c.park_type_str or '-'})")
    details_table.add_row("車位價格:", c.park_price or "-", "土地分區:", c.land_division or "-")
    details_table.add_row("座向規則:", c.direction_rule or "-", "管理費單價:", mgmt_fee_str)
    details_table.add_row("投資建設:", c.developer_company or "-", "營造廠:", c.builder_company or "-")
    details_table.add_row("建築設計:", c.architect_company or "-", "景觀/公設設計:", f"{c.landscape_name or '-'} / {c.postulate_name or '-'}")

    # 公設清單
    facility_str = "、".join(c.facilities) if c.facilities else "無公設資料"
    details_table.add_row("公設項目:", facility_str, "", "")

    return Panel(
        details_table,
        title=f"社區詳情 - {c.name}",
        border_style="cyan",
        box=box.ROUNDED,
    )


def community_to_dict(c: CommunityTable) -> Dict[str, Any]:
    """將 CommunityTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": c.id,
        "source_provider": c.source_provider,
        "source_id": c.source_id,
        "name": c.name,
        "housing_status": c.housing_status,
        "building_type": c.building_type,
        "build_purpose": c.build_purpose,
        "region_name": c.region_name,
        "section_name": c.section_name,
        "address": c.address,
        "lat": c.lat,
        "lng": c.lng,
        "avg_unit_price_wan": c.avg_unit_price_wan,
        "building_age_years": c.building_age_years,
        "shopping_district": c.shopping_district,
        "transport": c.transport,
        "total_households": c.total_households,
        "floor_plan": c.floor_plan,
        "structure": c.structure,
        "base_area_num": c.base_area_num,
        "base_area_pin": c.base_area_pin,
        "land_division": c.land_division,
        "park_price": c.park_price,
        "public_ratio_pct": c.public_ratio_pct,
        "parking_count": c.parking_count,
        "parking_ratio_pct": c.parking_ratio_pct,
        "park_type_str": c.park_type_str,
        "direction_rule": c.direction_rule,
        "manage_fee_per_pin": c.manage_fee_per_pin,
        "facilities": c.facilities,
        "developer_company": c.developer_company,
        "builder_company": c.builder_company,
        "architect_company": c.architect_company,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
