"""HouseLensAPI - 中古屋物件與刊登資料庫倉儲實作 (Property Repository Implementation)

純數值與純強型別入庫：零字串正則解析、零未清洗雜質！
"""

import uuid
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.storage.interfaces import IPropertyRepository
from src.storage.models.community import CommunityTable
from src.storage.models.property import PropertyListingTable, PropertyTable


class PropertyRepository(IPropertyRepository):
    """SQLAlchemy 2.0 非同步中古屋倉儲實作 (含純數值去重與多刊登聚合)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部房源刊登 ID 中已存在於資料庫者 (支援前綴標準化比對)"""
        if not external_ids:
            return set()

        lookup_ids = set(external_ids)
        for eid in external_ids:
            if eid.startswith("S"):
                lookup_ids.add(eid[1:])
            else:
                lookup_ids.add(f"S{eid}")

        stmt = select(PropertyListingTable.external_house_id).where(
            PropertyListingTable.provider_id == provider_id,
            PropertyListingTable.external_house_id.in_(list(lookup_ids)),
        )
        res = await self.session.execute(stmt)
        found_in_db = set(res.scalars().all())

        matched = set()
        for eid in external_ids:
            if (
                eid in found_in_db
                or (eid.startswith("S") and eid[1:] in found_in_db)
                or (f"S{eid}" in found_in_db)
            ):
                matched.add(eid)
        return matched

    async def find_duplicate_candidate(
        self,
        community_name: Optional[str] = None,
        floor_current: Optional[int] = None,
        rooms: Optional[int] = None,
        total_area_pin: Optional[float] = None,
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
        street: Optional[str] = None,
        floor_total: Optional[int] = None,
        area_tolerance_pct: float = 0.02,
        external_community_id: Optional[str] = None,
        is_whole_building: bool = False,
    ) -> Optional[PropertyTable]:
        """依外部社區代碼/社區名（第一級）或行政區路街總樓層（第二級無社區物件）、樓層純整數/整棟標記、房數純整數與坪數 (誤差 ±2%) 尋找可能之重複物理物件"""
        if total_area_pin is None:
            return None

        # 坪數誤差區間計算
        area_delta = total_area_pin * area_tolerance_pct
        min_area = total_area_pin - area_delta
        max_area = total_area_pin + area_delta

        # 第一級：同外部社區或同社區名稱比對
        if external_community_id or community_name:
            conds = [
                PropertyTable.total_area_pin >= min_area,
                PropertyTable.total_area_pin <= max_area,
            ]
            if external_community_id and community_name:
                conds.append(
                    or_(
                        PropertyTable.external_community_id == external_community_id,
                        PropertyTable.community_name == community_name,
                    )
                )
            elif external_community_id:
                conds.append(PropertyTable.external_community_id == external_community_id)
            else:
                conds.append(PropertyTable.community_name == community_name)

            stmt = select(PropertyTable).where(*conds)
            res = await self.session.execute(stmt)
            candidates = list(res.scalars().all())

            for cand in candidates:
                if is_whole_building:
                    if not cand.is_whole_building:
                        continue
                    if floor_total is not None and cand.floor_total is not None:
                        if cand.floor_total != floor_total:
                            continue
                else:
                    if cand.is_whole_building:
                        continue
                    if floor_current is not None and cand.floor_current is not None:
                        if cand.floor_current != floor_current:
                            continue
                if rooms is not None and cand.rooms is not None:
                    if cand.rooms != rooms:
                        continue
                return cand

        # 第二級：無社區物件之行政區、路街、樓層比對
        elif region_name and section_name and street:
            stmt = select(PropertyTable).where(
                PropertyTable.external_community_id.is_(None),
                PropertyTable.community_name.is_(None),
                PropertyTable.region_name == region_name,
                PropertyTable.section_name == section_name,
                PropertyTable.street == street,
                PropertyTable.total_area_pin >= min_area,
                PropertyTable.total_area_pin <= max_area,
            )
            res = await self.session.execute(stmt)
            candidates = list(res.scalars().all())

            for cand in candidates:
                if is_whole_building:
                    if not cand.is_whole_building:
                        continue
                    if floor_total is not None and cand.floor_total is not None:
                        if cand.floor_total != floor_total:
                            continue
                else:
                    if cand.is_whole_building:
                        continue
                    if floor_current is not None and cand.floor_current is not None:
                        if cand.floor_current != floor_current:
                            continue
                    if floor_total is not None and cand.floor_total is not None:
                        if cand.floor_total != floor_total:
                            continue
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
        target_external_id = summary.external_house_id if summary else detail.external_house_id
        listing_stmt = select(PropertyListingTable).where(
            PropertyListingTable.provider_id == provider_id,
            PropertyListingTable.external_house_id == target_external_id,
        )
        listing_res = await self.session.execute(listing_stmt)
        listing = listing_res.scalar_one_or_none()

        property_entity: Optional[PropertyTable] = None

        if listing is not None:
            property_entity = await self.get_by_id(listing.property_id)

        if property_entity is None:
            # 2. 刊登不存在，依領域服務去重結果掛載至既有實體
            if candidate_property_id:
                property_entity = await self.get_by_id(candidate_property_id)

        lat = detail.coordinates.lat if detail.coordinates else None
        lng = detail.coordinates.lng if detail.coordinates else None
        comm_name = summary.community_name if summary else detail.community_name
        ext_comm_id = summary.external_community_id if summary and summary.external_community_id else detail.external_community_id

        # 3. 查詢關聯社區實體內部外鍵 (UUID)
        matched_community_uuid: Optional[str] = None
        if ext_comm_id:
            comm_stmt = select(CommunityTable.id).where(
                or_(
                    CommunityTable.external_community_id == ext_comm_id,
                    CommunityTable.external_community_id == f"C{ext_comm_id}",
                    CommunityTable.external_community_id == ext_comm_id.lstrip("C"),
                )
            ).limit(1)
            comm_res = await self.session.execute(comm_stmt)
            matched_community_uuid = comm_res.scalar_one_or_none()

        if not matched_community_uuid and comm_name:
            comm_name_stmt = select(CommunityTable.id).where(CommunityTable.name == comm_name).limit(1)
            comm_name_res = await self.session.execute(comm_name_stmt)
            matched_community_uuid = comm_name_res.scalar_one_or_none()

        # 4. 若無既有物件，建立全新實體；否則以權威快照直接覆蓋
        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                external_house_id=target_external_id,
                community_uuid=matched_community_uuid,
                external_community_id=ext_comm_id,
                community_name=comm_name,
                is_whole_building=detail.is_whole_building,
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
                structure=detail.structure,
                orientation=detail.orientation,
                purpose=detail.purpose,
                current_state=detail.current_state,
                parking_desc=detail.parking_desc,
                main_area_pin=detail.main_area_pin,
                auxiliary_area_pin=detail.auxiliary_area_pin,
                common_area_pin=detail.common_area_pin,
                land_area_pin=detail.land_area_pin,
                parking_area_pin=detail.parking_area_pin,
                region_name=detail.region_name,
                section_name=detail.section_name,
                street=detail.street,
                address=detail.address,
                lat=lat,
                lng=lng,
                url=detail.url,
            )
            self.session.add(property_entity)
        else:
            # 權威快照覆蓋語意 (Authoritative Snapshot Override)
            if matched_community_uuid:
                property_entity.community_uuid = matched_community_uuid
            if ext_comm_id:
                property_entity.external_community_id = ext_comm_id
            if comm_name:
                property_entity.community_name = comm_name
            property_entity.is_whole_building = detail.is_whole_building

            property_entity.title = detail.title
            property_entity.price_wan = detail.price_wan
            property_entity.unit_price_wan = detail.unit_price_wan
            property_entity.total_area_pin = detail.total_area_pin
            property_entity.rooms = detail.rooms
            property_entity.living_rooms = detail.living_rooms
            property_entity.bathrooms = detail.bathrooms
            property_entity.balconies = detail.balconies
            property_entity.floor_current = detail.floor_current
            property_entity.floor_total = detail.floor_total
            property_entity.building_age_years = detail.building_age_years
            property_entity.management_fee_monthly = detail.management_fee_monthly
            property_entity.public_ratio_pct = detail.public_ratio_pct
            property_entity.has_lease = detail.has_lease
            property_entity.building_type = detail.building_type
            property_entity.structure = detail.structure
            property_entity.orientation = detail.orientation
            property_entity.purpose = detail.purpose
            property_entity.current_state = detail.current_state
            property_entity.parking_desc = detail.parking_desc
            property_entity.main_area_pin = detail.main_area_pin
            property_entity.auxiliary_area_pin = detail.auxiliary_area_pin
            property_entity.common_area_pin = detail.common_area_pin
            property_entity.land_area_pin = detail.land_area_pin
            property_entity.parking_area_pin = detail.parking_area_pin
            if detail.region_name:
                property_entity.region_name = detail.region_name
            if detail.section_name:
                property_entity.section_name = detail.section_name
            if detail.street:
                property_entity.street = detail.street
            if detail.address:
                property_entity.address = detail.address
            if lat is not None and lng is not None:
                property_entity.lat = lat
                property_entity.lng = lng
            if detail.url:
                property_entity.url = detail.url

        # 5. 同步更新或新增來源刊登紀錄
        cover_url = (summary.cover_image_url if summary else None) or detail.cover_image_url
        listing_price = summary.price_wan if summary else detail.price_wan
        listing_url = (summary.url if summary and summary.url else None) or detail.url

        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=target_external_id,
                listing_title=detail.title,
                listing_price_wan=listing_price,
                cover_image_url=cover_url,
                url=listing_url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = detail.title
            listing.listing_price_wan = listing_price
            if cover_url:
                listing.cover_image_url = cover_url
            if listing_url:
                listing.url = listing_url

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
            PropertyListingTable.external_house_id == summary.external_house_id,
        )
        listing_res = await self.session.execute(listing_stmt)
        listing = listing_res.scalar_one_or_none()

        property_entity: Optional[PropertyTable] = None
        if listing is not None:
            property_entity = await self.get_by_id(listing.property_id)

        if property_entity is None:
            if candidate_property_id:
                property_entity = await self.get_by_id(candidate_property_id)

        # 查詢關聯社區實體內部外鍵 (UUID)
        matched_community_uuid: Optional[str] = None
        if summary.external_community_id:
            comm_stmt = select(CommunityTable.id).where(
                or_(
                    CommunityTable.external_community_id == summary.external_community_id,
                    CommunityTable.external_community_id == f"C{summary.external_community_id}",
                    CommunityTable.external_community_id == summary.external_community_id.lstrip("C"),
                )
            ).limit(1)
            comm_res = await self.session.execute(comm_stmt)
            matched_community_uuid = comm_res.scalar_one_or_none()

        if not matched_community_uuid and summary.community_name:
            comm_name_stmt = select(CommunityTable.id).where(CommunityTable.name == summary.community_name).limit(1)
            comm_name_res = await self.session.execute(comm_name_stmt)
            matched_community_uuid = comm_name_res.scalar_one_or_none()

        if property_entity is None:
            property_entity = PropertyTable(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                external_house_id=summary.external_house_id,
                community_uuid=matched_community_uuid,
                external_community_id=summary.external_community_id,
                community_name=summary.community_name,
                is_whole_building=summary.is_whole_building,
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
                region_name=summary.region_name,
                section_name=summary.section_name,
                street=summary.street,
                address=summary.address,
                url=summary.url,
            )
            self.session.add(property_entity)
        else:
            if matched_community_uuid:
                property_entity.community_uuid = matched_community_uuid
            if summary.external_community_id:
                property_entity.external_community_id = summary.external_community_id
            if summary.community_name:
                property_entity.community_name = summary.community_name
            property_entity.is_whole_building = summary.is_whole_building
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
            if summary.region_name:
                property_entity.region_name = summary.region_name
            if summary.section_name:
                property_entity.section_name = summary.section_name
            if summary.url:
                property_entity.url = summary.url

        if listing is None:
            listing = PropertyListingTable(
                id=str(uuid.uuid4()),
                property_id=property_entity.id,
                provider_id=provider_id,
                external_house_id=summary.external_house_id,
                listing_title=summary.title,
                listing_price_wan=summary.price_wan,
                cover_image_url=summary.cover_image_url,
                url=summary.url,
            )
            listing.property = property_entity
            self.session.add(listing)
        else:
            listing.listing_title = summary.title
            listing.listing_price_wan = summary.price_wan
            if summary.cover_image_url:
                listing.cover_image_url = summary.cover_image_url
            if summary.url:
                listing.url = summary.url

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
        region_name: Optional[str] = None,
        section_name: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price_wan: Optional[int] = None,
        max_price_wan: Optional[int] = None,
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        rooms: Optional[int] = None,
        external_community_id: Optional[str] = None,
        community_uuid: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PropertyTable]:
        """多條件檢索庫存中古屋物件 (純數值查詢)"""
        stmt = select(PropertyTable)
        if region_name:
            stmt = stmt.where(PropertyTable.region_name == region_name)
        if section_name:
            stmt = stmt.where(PropertyTable.section_name == section_name)
        if external_community_id:
            stmt = stmt.where(PropertyTable.external_community_id == external_community_id)
        if community_uuid:
            stmt = stmt.where(PropertyTable.community_uuid == community_uuid)
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

    async def get_unlinked_community_properties(
        self,
        provider_id: Optional[str] = None,
        region_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[PropertyTable]:
        """查詢尚未關聯內部社區 UUID、但具備外部社區代碼或社區名稱之中古屋物件"""
        conds = [
            PropertyTable.community_uuid.is_(None),
            or_(
                PropertyTable.external_community_id.is_not(None),
                PropertyTable.community_name.is_not(None),
            ),
        ]
        if provider_id:
            conds.append(PropertyTable.provider_id == provider_id)
        if region_name:
            conds.append(PropertyTable.region_name == region_name)

        stmt = select(PropertyTable).where(*conds).order_by(PropertyTable.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def batch_update_community_links(
        self,
        property_ids: List[str],
        community_uuid: str,
        external_community_id: Optional[str] = None,
    ) -> int:
        """批次將特定房屋實體清單綁定至指定社區 UUID (並可選回填外部社區代碼)"""
        if not property_ids:
            return 0

        values_to_update: Dict[str, Any] = {"community_uuid": community_uuid}
        if external_community_id:
            values_to_update["external_community_id"] = external_community_id

        stmt = (
            update(PropertyTable)
            .where(PropertyTable.id.in_(property_ids))
            .values(**values_to_update)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount
