"""HouseLensAPI - 新建案資料庫倉儲實作 (New House Repository Implementation)"""

import uuid
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.new_house import NewHouseDetail, NewHouseSummary
from src.storage.interfaces import INewHouseRepository
from src.storage.models.new_house import NewHouseTable


class NewHouseRepository(INewHouseRepository):
    """SQLAlchemy 2.0 非同步新建案倉儲實作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_from_summary(
        self, summary: NewHouseSummary, provider_id: str
    ) -> NewHouseTable:
        """從 NewHouseSummary 新增或更新新建案基本資料"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.source_hid == summary.source_hid,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record is None:
            record = NewHouseTable(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                source_hid=summary.source_hid,
                project_name=summary.project_name,
                build_type=summary.project_status,
                region=summary.region_name,
                section=summary.section_name,
                address=summary.address,
                price=summary.price,
                area=summary.area,
                developer_company=summary.developer,
                cover_image_url=summary.cover_image_url,
                unit_price_str=None,
                parking_price_str=None,
            )
            self.session.add(record)
        else:
            record.project_name = summary.project_name
            record.build_type = summary.project_status
            record.region = summary.region_name
            record.section = summary.section_name
            record.address = summary.address
            if summary.price:
                record.price = summary.price
            if summary.area:
                record.area = summary.area
            if summary.developer:
                record.developer_company = summary.developer
            if summary.cover_image_url:
                record.cover_image_url = summary.cover_image_url

        await self.session.flush()
        return record

    async def upsert_from_detail(
        self, detail: NewHouseDetail, provider_id: str
    ) -> NewHouseTable:
        """從 NewHouseDetail 新增或更新新建案完整規劃規格"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.source_hid == detail.hid,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        layout_dump = [item.model_dump() for item in detail.layout_v2] if detail.layout_v2 else None

        if record is None:
            record = NewHouseTable(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                source_hid=detail.hid,
                project_name=detail.project_name,
                build_type=detail.build_type,
                region=detail.region,
                section=detail.section,
                address=detail.address,
                manage_cost=detail.manage_cost,
                structural_engine=detail.structural_engine,
                park_planning=detail.park_planning,
                direction_rule=detail.direction_rule,
                build_intro=detail.build_intro,
                park_ratio=detail.park_ratio,
                layout_v2=layout_dump,
                unit_price_str=detail.unit_price_str,
                parking_price_str=detail.parking_price_str,
                base_area_ping=detail.base_area_ping,
                public_ratio=detail.public_ratio,
                total_households=detail.total_households,
                developer_company=detail.developer_company,
                builder_company=detail.builder_company,
                architect_company=detail.architect_company,
                reception_address=detail.reception_address,
                community_id_ref=detail.community_id_ref,
            )
            self.session.add(record)
        else:
            record.project_name = detail.project_name
            record.build_type = detail.build_type
            if detail.region:
                record.region = detail.region
            if detail.section:
                record.section = detail.section
            if detail.address:
                record.address = detail.address

            record.manage_cost = detail.manage_cost or record.manage_cost
            record.structural_engine = detail.structural_engine or record.structural_engine
            record.park_planning = detail.park_planning or record.park_planning
            record.direction_rule = detail.direction_rule or record.direction_rule
            record.build_intro = detail.build_intro or record.build_intro
            record.park_ratio = detail.park_ratio or record.park_ratio
            if layout_dump:
                record.layout_v2 = layout_dump
            record.unit_price_str = detail.unit_price_str or record.unit_price_str
            record.parking_price_str = detail.parking_price_str or record.parking_price_str
            if detail.base_area_ping is not None:
                record.base_area_ping = detail.base_area_ping
            record.public_ratio = detail.public_ratio or record.public_ratio
            record.total_households = detail.total_households or record.total_households
            record.developer_company = detail.developer_company or record.developer_company
            record.builder_company = detail.builder_company or record.builder_company
            record.architect_company = detail.architect_company or record.architect_company
            record.reception_address = detail.reception_address or record.reception_address
            record.community_id_ref = detail.community_id_ref or record.community_id_ref

        await self.session.flush()
        return record

    async def get_by_id(self, new_house_id: str) -> Optional[NewHouseTable]:
        """根據內部主鍵 ID 查詢新建案"""
        stmt = select(NewHouseTable).where(NewHouseTable.id == new_house_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_source_hid(
        self, provider_id: str, source_hid: int
    ) -> Optional[NewHouseTable]:
        """根據來源建案 HID 查詢新建案"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.source_hid == source_hid,
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
    ) -> List[NewHouseTable]:
        """多條件檢索庫存新建案"""
        stmt = select(NewHouseTable)
        if region:
            stmt = stmt.where(NewHouseTable.region == region)
        if section:
            stmt = stmt.where(NewHouseTable.section == section)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    NewHouseTable.project_name.ilike(pattern),
                    NewHouseTable.address.ilike(pattern),
                    NewHouseTable.developer_company.ilike(pattern),
                )
            )

        stmt = stmt.order_by(NewHouseTable.updated_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
