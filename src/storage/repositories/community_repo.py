"""HouseLensAPI - 社區資料庫倉儲實作 (Community Repository Implementation)"""

import uuid
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.community import CommunityDetail, CommunitySummary
from src.storage.interfaces import ICommunityRepository
from src.storage.models.community import CommunityTable


class CommunityRepository(ICommunityRepository):
    """SQLAlchemy 2.0 非同步社區倉儲實作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_from_summary(
        self, summary: CommunitySummary, provider_id: str
    ) -> CommunityTable:
        """從 CommunitySummary 新增或更新社區節點"""
        stmt = select(CommunityTable).where(
            CommunityTable.source_provider == provider_id,
            CommunityTable.source_id == summary.community_id,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        lat = summary.coordinates.lat if summary.coordinates else None
        lng = summary.coordinates.lng if summary.coordinates else None

        if record is None:
            record = CommunityTable(
                id=str(uuid.uuid4()),
                source_provider=provider_id,
                source_id=summary.community_id,
                name=summary.community_name,
                build_purpose=summary.build_purpose_simple,
                build_type=summary.building_type_str,
                region_name=summary.region_name,
                section_name=summary.section_name,
                address=summary.full_address or summary.simple_address,
                lat=lat,
                lng=lng,
                avg_unit_price=summary.avg_unit_price,
                unit_price_unit=summary.unit_price_unit,
                shopping_district=summary.living_circle_name,
                transport=summary.nearest_station,
                cover_image_url=summary.cover_image_url,
            )
            self.session.add(record)
        else:
            record.name = summary.community_name
            if summary.build_purpose_simple:
                record.build_purpose = summary.build_purpose_simple
            if summary.building_type_str:
                record.build_type = summary.building_type_str
            if summary.region_name:
                record.region_name = summary.region_name
            if summary.section_name:
                record.section_name = summary.section_name
            if summary.full_address:
                record.address = summary.full_address
            if lat is not None and lng is not None:
                record.lat = lat
                record.lng = lng
            if summary.avg_unit_price is not None:
                record.avg_unit_price = summary.avg_unit_price
            if summary.unit_price_unit:
                record.unit_price_unit = summary.unit_price_unit
            if summary.living_circle_name:
                record.shopping_district = summary.living_circle_name
            if summary.nearest_station:
                record.transport = summary.nearest_station
            if summary.cover_image_url:
                record.cover_image_url = summary.cover_image_url

        await self.session.flush()
        return record

    async def upsert_from_detail(
        self, detail: CommunityDetail, provider_id: str
    ) -> CommunityTable:
        """從 CommunityDetail 新增或更新社區完整規格"""
        stmt = select(CommunityTable).where(
            CommunityTable.source_provider == provider_id,
            CommunityTable.source_id == detail.community_id,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record is None:
            record = CommunityTable(
                id=str(uuid.uuid4()),
                source_provider=provider_id,
                source_id=detail.community_id,
                name=detail.community_name,
                build_type=detail.build_type_str,
                build_purpose=detail.purpose_str,
                transport=detail.transport,
                address=detail.address,
                region_name=detail.region_name,
                section_name=detail.section_name,
                shopping_district=detail.shopping_district,
                park_rate=detail.park_rate,
                direction_rule=detail.direction_rule,
                build_intro=detail.build_intro,
                landscape_name=detail.landscape_name,
                postulate_name=detail.postulate_name,
                park_type_str=detail.park_type_str,
                age=detail.age,
                total_households=detail.total_households,
                floor_plan=detail.floor_plan,
                structure=detail.structure,
                base_area_ping=detail.base_area_ping,
                public_ratio=detail.public_ratio,
                parking_count=detail.parking_count,
                facilities=detail.facilities,
                developer_company=detail.developer_company,
                builder_company=detail.builder_company,
                architect_company=detail.architect_company,
                management_fee=detail.management_fee,
            )
            self.session.add(record)
        else:
            record.name = detail.community_name
            if detail.build_type_str:
                record.build_type = detail.build_type_str
            if detail.purpose_str:
                record.build_purpose = detail.purpose_str
            if detail.transport:
                record.transport = detail.transport
            if detail.address:
                record.address = detail.address
            if detail.region_name:
                record.region_name = detail.region_name
            if detail.section_name:
                record.section_name = detail.section_name
            if detail.shopping_district:
                record.shopping_district = detail.shopping_district

            # 更新規格欄位
            record.park_rate = detail.park_rate or record.park_rate
            record.direction_rule = detail.direction_rule or record.direction_rule
            record.build_intro = detail.build_intro or record.build_intro
            record.landscape_name = detail.landscape_name or record.landscape_name
            record.postulate_name = detail.postulate_name or record.postulate_name
            record.park_type_str = detail.park_type_str or record.park_type_str
            record.age = detail.age or record.age
            record.total_households = detail.total_households or record.total_households
            record.floor_plan = detail.floor_plan or record.floor_plan
            record.structure = detail.structure or record.structure
            record.base_area_ping = detail.base_area_ping or record.base_area_ping
            record.public_ratio = detail.public_ratio or record.public_ratio
            record.parking_count = detail.parking_count or record.parking_count
            if detail.facilities:
                record.facilities = detail.facilities
            record.developer_company = detail.developer_company or record.developer_company
            record.builder_company = detail.builder_company or record.builder_company
            record.architect_company = detail.architect_company or record.architect_company
            record.management_fee = detail.management_fee or record.management_fee

        await self.session.flush()
        return record

    async def get_by_id(self, community_id: str) -> Optional[CommunityTable]:
        """根據內部主鍵 ID 查詢社區"""
        stmt = select(CommunityTable).where(CommunityTable.id == community_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_source_id(
        self, provider_id: str, source_id: str
    ) -> Optional[CommunityTable]:
        """根據來源平台代碼與外部 ID 查詢社區"""
        stmt = select(CommunityTable).where(
            CommunityTable.source_provider == provider_id,
            CommunityTable.source_id == source_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def search(
        self,
        region: Optional[str] = None,
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityTable]:
        """多條件檢索庫存社區"""
        stmt = select(CommunityTable)
        if region:
            stmt = stmt.where(CommunityTable.region_name == region)
        if section:
            stmt = stmt.where(CommunityTable.section_name == section)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    CommunityTable.name.ilike(pattern),
                    CommunityTable.address.ilike(pattern),
                    CommunityTable.shopping_district.ilike(pattern),
                )
            )

        stmt = stmt.order_by(CommunityTable.updated_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
