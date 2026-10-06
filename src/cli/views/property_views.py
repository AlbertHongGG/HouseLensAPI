"""HouseLensAPI - 中古屋實體與跨平台比價 Rich 視圖渲染器 (Property Views)

純淨規範：以專業清晰之終端排版呈現，嚴禁使用裝飾性 emoji。
"""

from typing import Any, Dict, List
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from src.storage.models.property import PropertyTable


def render_property_table(properties: List[PropertyTable]) -> Table:
    """渲染中古屋實體庫存清單表格"""
    table = Table(
        title=f"中古屋物件實體列表 (共 {len(properties)} 筆)",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True,
    )

    table.add_column("外部編號 / 實體 ID", style="dim", max_width=18, overflow="ellipsis")
    table.add_column("標題 / 物件描述", style="bold white", max_width=30, overflow="ellipsis")
    table.add_column("所屬社區", style="cyan")
    table.add_column("總價", justify="right", style="bold green")
    table.add_column("單價", justify="right", style="yellow")
    table.add_column("權狀總坪", justify="right")
    table.add_column("格局 / 樓層", justify="center")
    table.add_column("屋齡", justify="center", style="cyan")
    table.add_column("刊登狀態", justify="center", style="bold white")

    for p in properties:
        listings_count = len(p.listings)
        badge = (
            f"[bold green]獨家 ({listings_count})[/bold green]"
            if listings_count <= 1
            else f"[bold magenta]聚合比價 ({listings_count}處)[/bold magenta]"
        )

        price_str = f"{p.price_wan} 萬"
        unit_price_str = f"{p.unit_price_wan:.1f} 萬/坪" if p.unit_price_wan else "-"
        area_str = f"{p.total_area_pin:.2f} 坪" if p.total_area_pin else "-"

        # 格局字串
        layout_parts = []
        if p.rooms is not None:
            layout_parts.append(f"{p.rooms}房")
        if p.living_rooms is not None:
            layout_parts.append(f"{p.living_rooms}廳")
        if p.bathrooms is not None:
            layout_parts.append(f"{p.bathrooms}衛")
        layout_str = "".join(layout_parts) if layout_parts else "-"

        # 樓層字串
        if p.floor_current is not None and p.floor_total is not None:
            floor_str = f"{p.floor_current}F/{p.floor_total}F"
        elif p.floor_current is not None:
            floor_str = f"{p.floor_current}F"
        else:
            floor_str = "-"

        specs = f"{layout_str} / {floor_str}"
        age_str = f"{p.building_age_years:.1f} 年" if p.building_age_years is not None else "-"
        id_display = f"[{p.provider_id}] {p.external_house_id}" if (p.provider_id and p.external_house_id) else (p.id[:8] + "...")

        table.add_row(
            id_display,
            p.title,
            p.community_name or "-",
            price_str,
            unit_price_str,
            area_str,
            specs,
            age_str,
            badge,
        )

    return table


def render_property_detail_view(p: PropertyTable) -> Group:
    """渲染中古屋詳細規格與跨平台刊登比價群組視圖"""
    specs_table = Table.grid(padding=(0, 2))
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")
    specs_table.add_column(style="bold cyan", justify="right")
    specs_table.add_column(style="white")

    coords_str = f"({p.lat:.5f}, {p.lng:.5f})" if p.lat and p.lng else "-"
    unit_price_str = f"{p.unit_price_wan:.1f} 萬/坪" if p.unit_price_wan else "-"
    total_area_str = f"{p.total_area_pin:.2f} 坪" if p.total_area_pin else "-"

    # 格局
    layout_parts = []
    if p.rooms is not None:
        layout_parts.append(f"{p.rooms}房")
    if p.living_rooms is not None:
        layout_parts.append(f"{p.living_rooms}廳")
    if p.bathrooms is not None:
        layout_parts.append(f"{p.bathrooms}衛")
    if p.balconies is not None:
        layout_parts.append(f"{p.balconies}陽台")
    layout_str = "".join(layout_parts) if layout_parts else "-"

    # 樓層
    if p.floor_current is not None and p.floor_total is not None:
        floor_str = f"{p.floor_current}F / 共{p.floor_total}F"
    elif p.floor_current is not None:
        floor_str = f"{p.floor_current}F"
    else:
        floor_str = "-"

    age_str = f"{p.building_age_years:.1f} 年" if p.building_age_years is not None else "-"
    mgmt_fee_str = f"{p.management_fee_monthly} 元/月" if p.management_fee_monthly is not None else "-"
    pub_ratio_str = f"{p.public_ratio_pct:.1f}%" if p.public_ratio_pct is not None else "-"
    lease_str = "帶租約" if p.has_lease is True else ("無租約" if p.has_lease is False else "-")

    id_disp = f"{p.id} [{p.provider_id}:{p.external_house_id}]" if (p.provider_id and p.external_house_id) else p.id
    specs_table.add_row("客觀實體 ID:", id_disp, "所屬社區:", p.community_name or "-")
    specs_table.add_row("刊登參考標題:", p.title, "參考總價:", f"[bold green]{p.price_wan} 萬元[/bold green]")
    specs_table.add_row("權狀登記總坪:", total_area_str, "參考單價:", unit_price_str)
    specs_table.add_row("格局規劃:", layout_str, "建物型態/結構:", f"{p.building_type or '-'} / {p.structure or '-'}")
    specs_table.add_row("所在樓層:", floor_str, "屋齡/座向:", f"{age_str} / {p.orientation or '-'}")
    specs_table.add_row("行政區地址:", f"{p.region_name or ''}{p.section_name or ''} {p.address or ''}", "地理座標:", coords_str)
    specs_table.add_row("管理費:", mgmt_fee_str, "公設比/現況:", f"{pub_ratio_str} / {p.current_state or '-'}")
    photo_count_str = f"{len(p.image_urls)} 張" if p.image_urls else "無"
    specs_table.add_row("相簿照片數量:", photo_count_str, "封面照片連結:", p.cover_image_url or "-")
    specs_table.add_row("原始物件網址:", p.url or "-", "", "")

    # 產權面積明細
    main_b = f"{p.main_area_pin:.2f}坪" if p.main_area_pin is not None else "-"
    aux_b = f"{p.auxiliary_area_pin:.2f}坪" if p.auxiliary_area_pin is not None else "-"
    com_b = f"{p.common_area_pin:.2f}坪" if p.common_area_pin is not None else "-"
    land_b = f"{p.land_area_pin:.2f}坪" if p.land_area_pin is not None else "-"
    park_b = f"{p.parking_area_pin:.2f}坪" if p.parking_area_pin is not None else "-"

    area_breakdown = (
        f"主建物: {main_b} │ "
        f"附屬建物: {aux_b} │ "
        f"共有部分: {com_b} │ "
        f"車位面積: {park_b} │ "
        f"土地持份: {land_b}"
    )
    specs_table.add_row("產權面積拆解:", f"[yellow]{area_breakdown}[/yellow]", "", "")

    property_panel = Panel(
        specs_table,
        title=f"客觀房屋實體資訊 - {p.title}",
        border_style="magenta",
        box=box.ROUNDED,
    )

    # 2. 跨平台來源刊登比價 Table (Listings Comparison)
    listings_table = Table(
        title="跨平台來源刊登明細與比價追蹤",
        box=box.SIMPLE_HEAD,
        header_style="bold yellow",
    )
    listings_table.add_column("來源平台", style="bold cyan", justify="center")
    listings_table.add_column("外部房源編號", style="white")
    listings_table.add_column("該刊登開出標題", style="white", max_width=35, overflow="ellipsis")
    listings_table.add_column("刊登開價", justify="right", style="bold green")
    listings_table.add_column("原始刊登網址", style="dim", max_width=35, overflow="ellipsis")
    listings_table.add_column("封面照片連結", style="dim", max_width=25, overflow="ellipsis")
    listings_table.add_column("更新時間", style="dim")

    for listing in p.listings:
        price_disp = f"{listing.listing_price_wan} 萬" if listing.listing_price_wan is not None else "-"
        listings_table.add_row(
            f"[{listing.provider_id.upper()}]",
            listing.external_house_id,
            listing.listing_title or "-",
            price_disp,
            listing.url or "-",
            listing.cover_image_url or "-",
            listing.updated_at.strftime("%Y-%m-%d %H:%M") if listing.updated_at else "-",
        )

    return Group(property_panel, listings_table)


def property_to_dict(p: PropertyTable) -> Dict[str, Any]:
    """將 PropertyTable 轉換為標準字典供 JSON 輸出"""
    return {
        "id": p.id,
        "provider_id": p.provider_id,
        "external_house_id": p.external_house_id,
        "community_uuid": p.community_uuid,
        "external_community_id": p.external_community_id,
        "community_name": p.community_name,
        "title": p.title,
        "price_wan": p.price_wan,
        "unit_price_wan": p.unit_price_wan,
        "total_area_pin": p.total_area_pin,
        "rooms": p.rooms,
        "living_rooms": p.living_rooms,
        "bathrooms": p.bathrooms,
        "balconies": p.balconies,
        "floor_current": p.floor_current,
        "floor_total": p.floor_total,
        "building_age_years": p.building_age_years,
        "management_fee_monthly": p.management_fee_monthly,
        "public_ratio_pct": p.public_ratio_pct,
        "has_lease": p.has_lease,
        "building_type": p.building_type,
        "structure": p.structure,
        "orientation": p.orientation,
        "purpose": p.purpose,
        "current_state": p.current_state,
        "parking_desc": p.parking_desc,
        "area_breakdown": {
            "main_area_pin": p.main_area_pin,
            "auxiliary_area_pin": p.auxiliary_area_pin,
            "common_area_pin": p.common_area_pin,
            "land_area_pin": p.land_area_pin,
            "parking_area_pin": p.parking_area_pin,
        },
        "region_name": p.region_name,
        "section_name": p.section_name,
        "street": p.street,
        "address": p.address,
        "lat": p.lat,
        "lng": p.lng,
        "cover_image_url": p.cover_image_url,
        "image_urls": p.image_urls or [],
        "url": p.url,
        "listings_count": len(p.listings),
        "listings": [
            {
                "id": it.id,
                "provider_id": it.provider_id,
                "external_house_id": it.external_house_id,
                "listing_title": it.listing_title,
                "listing_price_wan": it.listing_price_wan,
                "cover_image_url": it.cover_image_url,
                "image_urls": it.image_urls or [],
                "url": it.url,
                "updated_at": it.updated_at.isoformat() if it.updated_at else None,
            }
            for it in p.listings
        ],
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
