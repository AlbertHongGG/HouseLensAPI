"""HouseLensAPI - 中古屋物件與刊登資料庫倉儲實作 (Property Repository Implementation)"""

import uuid
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.sale_house import SaleHouseDetail, SaleHouseSummary
from src.storage.interfaces import IPropertyRepository
from src.storage.models.property import PropertyListingTable, PropertyTable


def normalize_floor(floor_str: Optional[str]) -> Optional[str]:
    """正規化樓層字串，例如 '2F/24F'、'2樓'、'2' 統一轉為 '2'"""
    if not floor_str:
        return None
    first = floor_str.split("/")[0].strip()
    clean = first.upper().replace("F", "").replace("樓", "").strip()
    return clean if clean else floor_str


def is_layout_compatible(l1: Optional[str], l2: Optional[str]) -> bool:
    """判斷兩種格局描述是否相容 (例如 '3房2廳2衛' 與 '3房2廳')"""
    if not l1 or not l2:
        return True
    if l1 == l2:
        return True
    if l1.startswith(l2) or l2.startswith(l1):
        return True
    if "房" in l1 and "房" in l2:
        r1 = l1.split("房")[0].strip()
        r2 = l2.split("房")[0].strip()
        return r1 == r2
    return False


class PropertyRepository(IPropertyRepository):
    """SQLAlchemy 2.0 非同步中古屋倉儲實作 (含自動去重與多刊登聚合)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_duplicate_candidate(
        self,
        community_name: Optional[str],
        floor: Optional[str],
        total_area: Optional[float],
        layout: Optional[str],
        area_tolerance_pct: float = 0.02,
    ) -> Optional[PropertyTable]:
        """依社區、樓層、格局與坪數 (誤差 ±2%) 尋找可能之重複物理物件"""
        if not community_name or total_area is None:
            return None

        # 坪數誤差區間計算
        area_delta = total_area * area_tolerance_pct
        min_area = total_area - area_delta
        max_area = total_area + area_delta

        stmt = select(PropertyTable).where(
            PropertyTable.community_name == community_name,
            PropertyTable.total_area >= min_area,
            PropertyTable.total_area <= max_area,
        )
        res = await self.session.execute(stmt)
        candidates = list(res.scalars().all())

        target_norm_floor = normalize_floor(floor)
        for cand in candidates:
            # 樓層比對
            cand_norm_floor = normalize_floor(cand.floor)
            if target_norm_floor and cand_norm_floor and target_norm_floor != cand_norm_floor:
                continue
            # 格局相容比對
            if not is_layout_compatible(cand.layout, layout):
                continue
            return cand

        return None

    async def upsert_property_with_listing(
        self,
        detail: SaleHouseDetail,
        provider_id: str,
        summary: Optional[SaleHouseSummary] = None,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """寫入物件完整詳情並同步維護來源刊登對應關係 (支援去重合併)"""
        # 1. 檢查此來源刊登是否已存在
        listing_stmt = select(PropertyListingTable).where(
            PropertyListingTable.provider_id == provider_id,
            PropertyListingTable.external_house_id == detail.house_id,
        )
        listing_res = await self.session.execute(listing_stmt)
        listing = listing_res.scalar_one_or_none()

        property_entity: Optional[PropertyTable] = None

        if listing is not None:
            # 刊登已存在，取得對應的主物件
            property_entity = await self.get_by_id(listing.property_id)

        if property_entity is None:
            # 2. 刊登不存在，尋找是否有可合併之既有物件
            if candidate_property_id:
                property_entity = await self.get_by_id(candidate_property_id)

            if property_entity is None:
                # 嘗試依特徵去重比對
                comm_name = summary.community_name if summary else None
                property_entity = await self.find_duplicate_candidate(
                    community_name=comm_name,
                    floor=detail.floor,
                    total_area=detail.total_area,
                    layout=detail.layout,
                )

        # 3. 若仍無既有物件，建立全新物件實體
        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                title=detail.title,
                price=detail.price,
                unit_price=detail.unit_price,
                total_area=detail.total_area,
                layout=detail.layout,
                building_type=detail.building_type,
                building_structure=detail.building_structure,
                floor=detail.floor,
                age=detail.age,
                orientation=detail.orientation,
                management_fee=detail.management_fee,
                public_ratio=detail.public_ratio,
                has_lease=detail.has_lease,
                balcony=detail.balcony,
                purpose=detail.purpose,
                current_state=detail.current_state,
                parking_desc=detail.parking_desc,
                main_building_area=detail.main_building_area,
                auxiliary_area=detail.auxiliary_area,
                common_area=detail.common_area,
                land_area=detail.land_area,
                parking_area=detail.parking_area,
                region=detail.region,
                section=detail.section,
                street=detail.street,
                address=detail.address,
                lat=detail.lat,
                lng=detail.lng,
                community_name=summary.community_name if summary else None,
            )
            self.session.add(property_entity)
        else:
            # 更新物件最新詳細規格
            property_entity.title = detail.title
            property_entity.price = detail.price
            property_entity.unit_price = detail.unit_price or property_entity.unit_price
            property_entity.total_area = detail.total_area or property_entity.total_area
            property_entity.layout = detail.layout or property_entity.layout
            property_entity.building_type = detail.building_type or property_entity.building_type
            property_entity.building_structure = (
                detail.building_structure or property_entity.building_structure
            )
            property_entity.floor = detail.floor or property_entity.floor
            property_entity.age = detail.age or property_entity.age
            property_entity.orientation = detail.orientation or property_entity.orientation
            property_entity.management_fee = detail.management_fee or property_entity.management_fee
            property_entity.public_ratio = detail.public_ratio or property_entity.public_ratio
            property_entity.has_lease = detail.has_lease or property_entity.has_lease
            property_entity.balcony = detail.balcony or property_entity.balcony
            property_entity.purpose = detail.purpose or property_entity.purpose
            property_entity.current_state = detail.current_state or property_entity.current_state
            property_entity.parking_desc = detail.parking_desc or property_entity.parking_desc
            property_entity.main_building_area = (
                detail.main_building_area or property_entity.main_building_area
            )
            property_entity.auxiliary_area = (
                detail.auxiliary_area or property_entity.auxiliary_area
            )
            property_entity.common_area = detail.common_area or property_entity.common_area
            property_entity.land_area = detail.land_area or property_entity.land_area
            property_entity.parking_area = detail.parking_area or property_entity.parking_area
            if detail.region:
                property_entity.region = detail.region
            if detail.section:
                property_entity.section = detail.section
            if detail.street:
                property_entity.street = detail.street
            if detail.address:
                property_entity.address = detail.address
            if detail.lat is not None and detail.lng is not None:
                property_entity.lat = detail.lat
                property_entity.lng = detail.lng

        # 4. 同步更新或新增來源刊登紀錄
        cover_url = summary.cover_image_url if summary else None
        listing_price_str = summary.price if summary else f"{detail.price}萬元"
        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=detail.house_id,
                listing_title=detail.title,
                listing_price=listing_price_str,
                cover_image_url=cover_url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = detail.title
            listing.listing_price = listing_price_str
            if cover_url:
                listing.cover_image_url = cover_url

        await self.session.flush()
        self.session.expire(property_entity, ["listings"])
        loaded = await self.get_by_id(property_entity.id)
        return loaded or property_entity

    async def upsert_from_summary(
        self,
        summary: SaleHouseSummary,
        provider_id: str,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """從清單 Summary 寫入或更新物件與刊登"""
        # 1. 檢查刊登是否存在
        listing_stmt = select(PropertyListingTable).where(
            PropertyListingTable.provider_id == provider_id,
            PropertyListingTable.external_house_id == summary.house_id,
        )
        listing_res = await self.session.execute(listing_stmt)
        listing = listing_res.scalar_one_or_none()

        property_entity: Optional[PropertyTable] = None
        if listing is not None:
            property_entity = await self.get_by_id(listing.property_id)

        if property_entity is None:
            if candidate_property_id:
                property_entity = await self.get_by_id(candidate_property_id)
            if property_entity is None:
                property_entity = await self.find_duplicate_candidate(
                    community_name=summary.community_name,
                    floor=summary.floor,
                    total_area=summary.total_area,
                    layout=summary.layout,
                )

        # 價格整數防禦轉換 (例如 "5,258萬元" -> 5258)
        clean_price = 0
        digits = "".join(ch for ch in summary.price if ch.isdigit())
        if digits:
            try:
                clean_price = int(digits)
            except ValueError:
                clean_price = 0

        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                title=summary.title,
                price=clean_price,
                unit_price=summary.unit_price,
                total_area=summary.total_area,
                layout=summary.layout,
                building_type=summary.building_type,
                floor=summary.floor,
                region=summary.region,
                section=summary.section,
                street=summary.street,
                address=summary.address,
                community_name=summary.community_name,
            )
            self.session.add(property_entity)
        else:
            if clean_price > 0:
                property_entity.price = clean_price
            if summary.unit_price:
                property_entity.unit_price = summary.unit_price
            if summary.total_area is not None:
                property_entity.total_area = summary.total_area

        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=summary.house_id,
                listing_title=summary.title,
                listing_price=summary.price,
                cover_image_url=summary.cover_image_url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = summary.title
            listing.listing_price = summary.price
            if summary.cover_image_url:
                listing.cover_image_url = summary.cover_image_url

        await self.session.flush()
        self.session.expire(property_entity, ["listings"])
        loaded = await self.get_by_id(property_entity.id)
        return loaded or property_entity

    async def get_by_id(self, property_id: str) -> Optional[PropertyTable]:
        """根據內部主鍵 ID 查詢客觀物件實體"""
        stmt = (
            select(PropertyTable)
            .options(selectinload(PropertyTable.listings))
            .where(PropertyTable.id == property_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_listing(
        self, provider_id: str, external_house_id: str
    ) -> Optional[PropertyTable]:
        """根據來源平台刊登 ID 查詢關聯之客觀物件"""
        stmt = (
            select(PropertyTable)
            .options(selectinload(PropertyTable.listings))
            .join(PropertyListingTable, PropertyTable.id == PropertyListingTable.property_id)
            .where(
                PropertyListingTable.provider_id == provider_id,
                PropertyListingTable.external_house_id == external_house_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def search(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """多條件檢索庫存中古屋物件"""
        stmt = select(PropertyTable)
        if region:
            stmt = stmt.where(PropertyTable.region == region)
        if section:
            stmt = stmt.where(PropertyTable.section == section)
        if min_price is not None:
            stmt = stmt.where(PropertyTable.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(PropertyTable.price <= max_price)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    PropertyTable.title.ilike(pattern),
                    PropertyTable.community_name.ilike(pattern),
                    PropertyTable.address.ilike(pattern),
                )
            )

        stmt = stmt.order_by(PropertyTable.updated_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
