"""HouseLensAPI - 中古屋實體與跨平台比價 Rich 視圖渲染器 (Property Views)"""

from typing import Any, Dict, List
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from src.storage.models.property import PropertyTable


def render_property_table(properties: List[PropertyTable]) -> Table:
    """渲染中古屋實體庫存清單表格 (含關聯刊登數量徽章)"""
    table = Table(
        title=f"🏡 庫存中古屋物件實體 (共 {len(properties)} 棟/戶)",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True,
    )

    table.add_column("實體 ID", style="dim", max_width=10, overflow="ellipsis")
    table.add_column("標題 / 物件描述", style="bold white", max_width=30, overflow="ellipsis")
    table.add_column("所屬社區", style="cyan")
    table.add_column("總價", justify="right", style="bold green")
    table.add_column("單價", justify="right", style="yellow")
    table.add_column("權狀總坪", justify="right")
    table.add_column("格局 / 樓層", justify="center")
    table.add_column("跨平台刊登數", justify="center", style="bold white")

    for p in properties:
        listings_count = len(p.listings)
        badge = (
            f"[bold green]✔ 獨家 ({listings_count})[/bold green]"
            if listings_count <= 1
            else f"[bold magenta]⚡ 聚合比價 ({listings_count}處)[/bold magenta]"
        )

        price_str = f"{p.price} 萬元"
        area_str = f"{p.total_area:.2f} 坪" if p.total_area else "-"
        specs = f"{p.layout or '-'} / {p.floor or '-'}"

        table.add_row(
            p.id[:8] + "...",
            p.title,
            p.community_name or "-",
            price_str,
            p.unit_price or "-",
            area_str,
            specs,
            badge,
        )

    return table


def render_property_detail_view(p: PropertyTable) -> Group:
    """渲染中古屋詳細規格與跨平台刊登比價群組視圖"""
    # 1. 客觀物理規格 Table
    specs_table = Table.grid(padding=(0, 2))
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")

    coords_str = f"({p.lat:.5f}, {p.lng:.5f})" if p.lat and p.lng else "-"
    specs_table.add_row("客觀實體 ID:", p.id, "所屬社區:", p.community_name or "-")
    specs_table.add_row("刊登參考標題:", p.title, "參考總價:", f"[bold green]{p.price} 萬元[/bold green]")
    specs_table.add_row("權狀登記總坪:", f"{p.total_area or '-'} 坪", "參考單價:", p.unit_price or "-")
    specs_table.add_row("格局規劃:", p.layout or "-", "建物型態/結構:", f"{p.building_type or '-'} / {p.building_structure or '-'}")
    specs_table.add_row("所在樓層:", p.floor or "-", "屋齡/座向:", f"{p.age or '-'} / {p.orientation or '-'}")
    specs_table.add_row("行政區地址:", f"{p.region or ''}{p.section or ''} {p.address or ''}", "地理座標:", coords_str)
    specs_table.add_row("管理費:", p.management_fee or "-", "公設比/陽台:", f"{p.public_ratio or '-'} / {p.balcony or '-'}")
    specs_table.add_row("帶租約現況:", f"{p.has_lease or '-'} / {p.current_state or '-'}", "車位規格說明:", p.parking_desc or "-")

    # 產權面積明細
    area_breakdown = (
        f"主建物: {p.main_building_area or '-'} │ "
        f"附屬建物: {p.auxiliary_area or '-'} │ "
        f"共有部分: {p.common_area or '-'} │ "
        f"車位面積: {p.parking_area or '-'} │ "
        f"土地持份: {p.land_area or '-'}"
    )
    specs_table.add_row("產權面積拆解:", f"[yellow]{area_breakdown}[/yellow]", "", "")

    property_panel = Panel(
        specs_table,
        title=f"🏡 客觀房屋實體資訊 - {p.title}",
        border_style="magenta",
        box=box.ROUNDED,
    )

    # 2. 跨平台來源刊登比價 Table (Listings Comparison)
    listings_table = Table(
        title="🔍 跨平台來源刊登明細與比價追蹤 (Listing References)",
        box=box.SIMPLE_HEAD,
        header_style="bold yellow",
    )
    listings_table.add_column("來源平台", style="bold cyan", justify="center")
    listings_table.add_column("外部房源編號", style="white")
    listings_table.add_column("該刊登開出標題", style="white", max_width=40, overflow="ellipsis")
    listings_table.add_column("刊登開價", justify="right", style="bold green")
    listings_table.add_column("封面照片連結", style="dim", max_width=30, overflow="ellipsis")
    listings_table.add_column("更新時間", style="dim")

    for listing in p.listings:
        listings_table.add_row(
            f"[{listing.provider_id.upper()}]",
            listing.external_house_id,
            listing.listing_title or "-",
            listing.listing_price or "-",
            listing.cover_image_url or "-",
            listing.updated_at.strftime("%Y-%m-%d %H:%M") if listing.updated_at else "-",
        )

    return Group(property_panel, listings_table)


def property_to_dict(p: PropertyTable) -> Dict[str, Any]:
    """將 PropertyTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": p.id,
        "community_name": p.community_name,
        "title": p.title,
        "price_wan": p.price,
        "unit_price": p.unit_price,
        "total_area": p.total_area,
        "layout": p.layout,
        "building_type": p.building_type,
        "building_structure": p.building_structure,
        "floor": p.floor,
        "age": p.age,
        "orientation": p.orientation,
        "management_fee": p.management_fee,
        "public_ratio": p.public_ratio,
        "has_lease": p.has_lease,
        "balcony": p.balcony,
        "purpose": p.purpose,
        "current_state": p.current_state,
        "parking_desc": p.parking_desc,
        "area_breakdown": {
            "main_building": p.main_building_area,
            "auxiliary": p.auxiliary_area,
            "common": p.common_area,
            "land": p.land_area,
            "parking": p.parking_area,
        },
        "region": p.region,
        "section": p.section,
        "address": p.address,
        "lat": p.lat,
        "lng": p.lng,
        "listings_count": len(p.listings),
        "listings": [
            {
                "id": it.id,
                "provider_id": it.provider_id,
                "external_house_id": it.external_house_id,
                "listing_title": it.listing_title,
                "listing_price": it.listing_price,
                "cover_image_url": it.cover_image_url,
                "updated_at": it.updated_at.isoformat() if it.updated_at else None,
            }
            for it in p.listings
        ],
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
