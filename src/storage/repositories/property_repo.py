"""HouseLensAPI - 中古屋物件與刊登資料庫倉儲實作 (Property Repository Implementation)

純數值與純強型別入庫：零字串正則解析、零未清洗雜質！
"""

import uuid
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.storage.interfaces import IPropertyRepository
from src.storage.models.property import PropertyListingTable, PropertyTable


class PropertyRepository(IPropertyRepository):
    """SQLAlchemy 2.0 非同步中古屋倉儲實作 (含純數值去重與多刊登聚合)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_duplicate_candidate(
        self,
        community_name: Optional[str],
        floor_current: Optional[int],
        rooms: Optional[int],
        total_area_pin: Optional[float],
        area_tolerance_pct: float = 0.02,
    ) -> Optional[PropertyTable]:
        """依社區、樓層純整數、房數純整數與坪數 (誤差 ±2%) 尋找可能之重複物理物件"""
        if not community_name or total_area_pin is None:
            return None

        # 坪數誤差區間計算
        area_delta = total_area_pin * area_tolerance_pct
        min_area = total_area_pin - area_delta
        max_area = total_area_pin + area_delta

        stmt = select(PropertyTable).where(
            PropertyTable.community_name == community_name,
            PropertyTable.total_area_pin >= min_area,
            PropertyTable.total_area_pin <= max_area,
        )
        res = await self.session.execute(stmt)
        candidates = list(res.scalars().all())

        for cand in candidates:
            # 樓層純整數比對
            if floor_current is not None and cand.floor_current is not None:
                if cand.floor_current != floor_current:
                    continue
            # 格局房數純整數比對
            if rooms is not None and cand.rooms is not None:
                if cand.rooms != rooms:
                    continue
            return cand

        return None

    async def upsert_property_with_listing(
        self,
        detail: NormalizedSalePropertyDetail,
        provider_id: str,
        summary: Optional[NormalizedSaleListing] = None,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """寫入物件完整詳情並同步維護來源刊登對應關係 (支援純數值去重合併)"""
        # 1. 檢查此來源刊登是否已存在
        listing_stmt = select(PropertyListingTable).where(
            PropertyListingTable.provider_id == provider_id,
            PropertyListingTable.external_house_id == detail.house_id,
        )
        listing_res = await self.session.execute(listing_stmt)
        listing = listing_res.scalar_one_or_none()

        property_entity: Optional[PropertyTable] = None

        if listing is not None:
            property_entity = await self.get_by_id(listing.property_id)

        if property_entity is None:
            # 2. 刊登不存在，尋找是否有可合併之既有物件
            if candidate_property_id:
                property_entity = await self.get_by_id(candidate_property_id)

            if property_entity is None:
                comm_name = summary.community_name if summary else detail.community_name
                property_entity = await self.find_duplicate_candidate(
                    community_name=comm_name,
                    floor_current=detail.floor_current,
                    rooms=detail.rooms,
                    total_area_pin=detail.total_area_pin,
                )

        lat = detail.coordinates.lat if detail.coordinates else None
        lng = detail.coordinates.lng if detail.coordinates else None
        comm_name = summary.community_name if summary else detail.community_name

        # 3. 若仍無既有物件，建立全新物件實體
        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                title=detail.title,
                price_wan=detail.price_wan,
                unit_price_wan=detail.unit_price_wan,
                total_area_pin=detail.total_area_pin,
                rooms=detail.rooms,
                living_rooms=detail.living_rooms,
                bathrooms=detail.bathrooms,
                balconies=detail.balconies,
                floor_current=detail.floor_current,
                floor_total=detail.floor_total,
                building_age_years=detail.building_age_years,
                management_fee_monthly=detail.management_fee_monthly,
                public_ratio_pct=detail.public_ratio_pct,
                has_lease=detail.has_lease,
                building_type=detail.building_type,
                building_structure=detail.building_structure,
                orientation=detail.orientation,
                purpose=detail.purpose,
                current_state=detail.current_state,
                parking_desc=detail.parking_desc,
                main_area_pin=detail.main_area_pin,
                auxiliary_area_pin=detail.auxiliary_area_pin,
                common_area_pin=detail.common_area_pin,
                land_area_pin=detail.land_area_pin,
                parking_area_pin=detail.parking_area_pin,
                region=detail.region,
                section=detail.section,
                street=detail.street,
                address=detail.address,
                lat=lat,
                lng=lng,
                community_name=comm_name,
            )
            self.session.add(property_entity)
        else:
            # 更新最新詳細規格 (純覆寫或優化)
            property_entity.title = detail.title
            property_entity.price_wan = detail.price_wan
            if detail.unit_price_wan is not None:
                property_entity.unit_price_wan = detail.unit_price_wan
            if detail.total_area_pin is not None:
                property_entity.total_area_pin = detail.total_area_pin
            if detail.rooms is not None:
                property_entity.rooms = detail.rooms
            if detail.living_rooms is not None:
                property_entity.living_rooms = detail.living_rooms
            if detail.bathrooms is not None:
                property_entity.bathrooms = detail.bathrooms
            if detail.balconies is not None:
                property_entity.balconies = detail.balconies
            if detail.floor_current is not None:
                property_entity.floor_current = detail.floor_current
            if detail.floor_total is not None:
                property_entity.floor_total = detail.floor_total
            if detail.building_age_years is not None:
                property_entity.building_age_years = detail.building_age_years
            if detail.management_fee_monthly is not None:
                property_entity.management_fee_monthly = detail.management_fee_monthly
            if detail.public_ratio_pct is not None:
                property_entity.public_ratio_pct = detail.public_ratio_pct
            if detail.has_lease is not None:
                property_entity.has_lease = detail.has_lease
            if detail.building_type:
                property_entity.building_type = detail.building_type
            if detail.building_structure:
                property_entity.building_structure = detail.building_structure
            if detail.orientation:
                property_entity.orientation = detail.orientation
            if detail.purpose:
                property_entity.purpose = detail.purpose
            if detail.current_state:
                property_entity.current_state = detail.current_state
            if detail.parking_desc:
                property_entity.parking_desc = detail.parking_desc
            if detail.main_area_pin is not None:
                property_entity.main_area_pin = detail.main_area_pin
            if detail.auxiliary_area_pin is not None:
                property_entity.auxiliary_area_pin = detail.auxiliary_area_pin
            if detail.common_area_pin is not None:
                property_entity.common_area_pin = detail.common_area_pin
            if detail.land_area_pin is not None:
                property_entity.land_area_pin = detail.land_area_pin
            if detail.parking_area_pin is not None:
                property_entity.parking_area_pin = detail.parking_area_pin
            if detail.region:
                property_entity.region = detail.region
            if detail.section:
                property_entity.section = detail.section
            if detail.street:
                property_entity.street = detail.street
            if detail.address:
                property_entity.address = detail.address
            if lat is not None and lng is not None:
                property_entity.lat = lat
                property_entity.lng = lng

        # 4. 同步更新或新增來源刊登紀錄
        cover_url = summary.cover_image_url if summary else None
        listing_price = summary.price_wan if summary else detail.price_wan

        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=detail.house_id,
                listing_title=detail.title,
                listing_price_wan=listing_price,
                cover_image_url=cover_url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = detail.title
            listing.listing_price_wan = listing_price
            if cover_url:
                listing.cover_image_url = cover_url

        await self.session.flush()
        self.session.expire(property_entity, ["listings"])
        loaded = await self.get_by_id(property_entity.id)
        return loaded or property_entity

    async def upsert_from_summary(
        self,
        summary: NormalizedSaleListing,
        provider_id: str,
        candidate_property_id: Optional[str] = None,
    ) -> PropertyTable:
        """從清單 Summary 寫入或更新物件與刊登"""
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
                    floor_current=summary.floor_current,
                    rooms=summary.rooms,
                    total_area_pin=summary.total_area_pin,
                )

        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                title=summary.title,
                price_wan=summary.price_wan,
                unit_price_wan=summary.unit_price_wan,
                total_area_pin=summary.total_area_pin,
                rooms=summary.rooms,
                living_rooms=summary.living_rooms,
                bathrooms=summary.bathrooms,
                floor_current=summary.floor_current,
                floor_total=summary.floor_total,
                building_type=summary.building_type,
                building_age_years=summary.building_age_years,
                region=summary.region,
                section=summary.section,
                street=summary.street,
                address=summary.address,
                community_name=summary.community_name,
            )
            self.session.add(property_entity)
        else:
            if summary.price_wan > 0:
                property_entity.price_wan = summary.price_wan
            if summary.unit_price_wan is not None:
                property_entity.unit_price_wan = summary.unit_price_wan
            if summary.total_area_pin is not None:
                property_entity.total_area_pin = summary.total_area_pin
            if summary.floor_current is not None:
                property_entity.floor_current = summary.floor_current
            if summary.floor_total is not None:
                property_entity.floor_total = summary.floor_total
            if summary.rooms is not None:
                property_entity.rooms = summary.rooms
            if summary.living_rooms is not None:
                property_entity.living_rooms = summary.living_rooms
            if summary.bathrooms is not None:
                property_entity.bathrooms = summary.bathrooms
            if summary.building_age_years is not None:
                property_entity.building_age_years = summary.building_age_years

        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=summary.house_id,
                listing_title=summary.title,
                listing_price_wan=summary.price_wan,
                cover_image_url=summary.cover_image_url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = summary.title
            listing.listing_price_wan = summary.price_wan
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
        min_price_wan: Optional[int] = None,
        max_price_wan: Optional[int] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        rooms: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """多條件檢索庫存中古屋物件 (純數值查詢)"""
        stmt = select(PropertyTable)
        if region:
            stmt = stmt.where(PropertyTable.region == region)
        if section:
            stmt = stmt.where(PropertyTable.section == section)
        if min_price_wan is not None:
            stmt = stmt.where(PropertyTable.price_wan >= min_price_wan)
        if max_price_wan is not None:
            stmt = stmt.where(PropertyTable.price_wan <= max_price_wan)
        if min_age_years is not None:
            stmt = stmt.where(PropertyTable.building_age_years >= min_age_years)
        if max_age_years is not None:
            stmt = stmt.where(PropertyTable.building_age_years <= max_age_years)
        if rooms is not None:
            stmt = stmt.where(PropertyTable.rooms == rooms)
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
