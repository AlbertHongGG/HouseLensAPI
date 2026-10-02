"""HouseLensAPI - 新建案資料庫倉儲實作 (New House Repository Implementation)

純數值與純強型別入庫：零字串正則解析、零未清洗雜質！
"""

import uuid
from typing import List, Optional, Set
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.new_house import (
    NormalizedNewHouseDetail,
    NormalizedNewHouseSummary,
)
from src.storage.interfaces import INewHouseRepository
from src.storage.models.new_house import NewHouseTable


class NewHouseRepository(INewHouseRepository):
    """SQLAlchemy 2.0 非同步新建案倉儲實作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部新建案 HID 中已存在於資料庫者"""
        if not external_ids:
            return set()
        int_ids = [int(i) for i in external_ids if str(i).isdigit()]
        if not int_ids:
            return set()
        stmt = select(NewHouseTable.source_hid).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.source_hid.in_(int_ids),
        )
        res = await self.session.execute(stmt)
        return {str(x) for x in res.scalars().all()}

    async def upsert_from_summary(
        self, summary: NormalizedNewHouseSummary, provider_id: str
    ) -> NewHouseTable:
        """從 NormalizedNewHouseSummary 新增或更新新建案基本資料"""
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
                min_unit_price_wan=summary.min_unit_price_wan,
                max_unit_price_wan=summary.max_unit_price_wan,
                min_area_pin=summary.min_area_pin,
                max_area_pin=summary.max_area_pin,
                developer_company=summary.developer,
                cover_image_url=summary.cover_image_url,
            )
            self.session.add(record)
        else:
            record.project_name = summary.project_name
            record.build_type = summary.project_status
            record.region = summary.region_name
            record.section = summary.section_name
            record.address = summary.address
            if summary.min_unit_price_wan is not None:
                record.min_unit_price_wan = summary.min_unit_price_wan
            if summary.max_unit_price_wan is not None:
                record.max_unit_price_wan = summary.max_unit_price_wan
            if summary.min_area_pin is not None:
                record.min_area_pin = summary.min_area_pin
            if summary.max_area_pin is not None:
                record.max_area_pin = summary.max_area_pin
            if summary.developer:
                record.developer_company = summary.developer
            if summary.cover_image_url:
                record.cover_image_url = summary.cover_image_url

        await self.session.flush()
        return record

    async def upsert_from_detail(
        self, detail: NormalizedNewHouseDetail, provider_id: str
    ) -> NewHouseTable:
        """從 NormalizedNewHouseDetail 新增或更新新建案完整規劃規格"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.source_hid == detail.hid,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        layouts_dump = [item.model_dump() for item in detail.layouts] if detail.layouts else None

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
                base_area_pin=detail.base_area_pin,
                public_ratio_pct=detail.public_ratio_pct,
                total_households=detail.total_households,
                manage_fee_per_pin=detail.manage_fee_per_pin,
                min_unit_price_wan=detail.min_unit_price_wan,
                max_unit_price_wan=detail.max_unit_price_wan,
                layouts=layouts_dump,
                structural_engine=detail.structural_engine,
                direction_rule=detail.direction_rule,
                developer_company=detail.developer_company,
                builder_company=detail.builder_company,
                architect_company=detail.architect_company,
                reception_address=detail.reception_address,
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

            # 數值更新
            if detail.base_area_pin is not None:
                record.base_area_pin = detail.base_area_pin
            if detail.public_ratio_pct is not None:
                record.public_ratio_pct = detail.public_ratio_pct
            if detail.total_households is not None:
                record.total_households = detail.total_households
            if detail.manage_fee_per_pin is not None:
                record.manage_fee_per_pin = detail.manage_fee_per_pin
            if detail.min_unit_price_wan is not None:
                record.min_unit_price_wan = detail.min_unit_price_wan
            if detail.max_unit_price_wan is not None:
                record.max_unit_price_wan = detail.max_unit_price_wan

            # 結構化房型
            if layouts_dump is not None:
                record.layouts = layouts_dump

            # 描述更新
            if detail.structural_engine:
                record.structural_engine = detail.structural_engine
            if detail.direction_rule:
                record.direction_rule = detail.direction_rule
            if detail.developer_company:
                record.developer_company = detail.developer_company
            if detail.builder_company:
                record.builder_company = detail.builder_company
            if detail.architect_company:
                record.architect_company = detail.architect_company
            if detail.reception_address:
                record.reception_address = detail.reception_address

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
