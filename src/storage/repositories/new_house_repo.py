"""HouseLensAPI - 新建案資料庫倉儲實作 (New House Repository Implementation)

純數值與純強型別入庫：零字串正則解析、零未清洗雜質！
"""

import uuid
from typing import List, Optional, Set
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.new_house import NormalizedNewHouseDetail
from src.storage.interfaces import INewHouseRepository
from src.storage.models.new_house import NewHouseTable


class NewHouseRepository(INewHouseRepository):
    """SQLAlchemy 2.0 非同步新建案倉儲實作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部新建案專案 ID 中已存在於資料庫者"""
        if not external_ids:
            return set()
        stmt = select(NewHouseTable.external_project_id).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.external_project_id.in_(external_ids),
        )
        res = await self.session.execute(stmt)
        return set(res.scalars().all())

    async def upsert_from_detail(
        self, detail: NormalizedNewHouseDetail, provider_id: str
    ) -> NewHouseTable:
        """從 NormalizedNewHouseDetail 新增或更新新建案完整規劃規格"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.external_project_id == detail.external_project_id,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        layouts_dump = [item.model_dump() for item in detail.layouts] if detail.layouts else None

        if record is None:
            record = NewHouseTable(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                external_project_id=detail.external_project_id,
                name=detail.name,
                housing_status=detail.housing_status,
                building_type=detail.building_type,
                purpose=detail.purpose,
                land_division=detail.land_division,
                region_name=detail.region_name,
                section_name=detail.section_name,
                address=detail.address,
                min_area_pin=detail.min_area_pin,
                max_area_pin=detail.max_area_pin,
                cover_image_url=detail.cover_image_url,
                image_urls=detail.image_urls if detail.image_urls else None,
                url=detail.url,
                handover_time=detail.handover_time,
                open_sell_date=detail.open_sell_date,
                base_area_pin=detail.base_area_pin,
                public_ratio_pct=detail.public_ratio_pct,
                total_households=detail.total_households,
                manage_fee_per_pin=detail.manage_fee_per_pin,
                min_unit_price_wan=detail.min_unit_price_wan,
                max_unit_price_wan=detail.max_unit_price_wan,
                min_parking_price_wan=detail.parking.min_parking_price_wan if detail.parking else None,
                max_parking_price_wan=detail.parking.max_parking_price_wan if detail.parking else None,
                parking_ratio_desc=detail.parking.parking_ratio_desc if detail.parking else None,
                parking_ratio=detail.parking.parking_ratio if detail.parking else None,
                parking_planning_desc=detail.parking.parking_planning_desc if detail.parking else None,
                plane_parking_count=detail.parking.plane_parking_count if detail.parking else None,
                mechanical_parking_count=detail.parking.mechanical_parking_count if detail.parking else None,
                charging_piles_desc=detail.parking.charging_piles_desc if detail.parking else None,
                has_charging_piles=detail.parking.has_charging_piles if detail.parking else None,
                parking_type=detail.parking.parking_type if detail.parking else None,
                layouts=layouts_dump,
                structure=detail.structure,
                orientation=detail.orientation,
                developer_company=detail.developer_company,
                builder_company=detail.builder_company,
                architect_company=detail.architect_company,
                sales_agency_company=detail.sales_agency_company,
                reception_address=detail.reception_address,
                community_uuid=detail.community_uuid,
                external_community_id=detail.external_community_id,
                community_name=detail.community_name,
                community_age=detail.community_age,
                lat=detail.lat,
                lng=detail.lng,
            )
            self.session.add(record)
        else:
            record.name = detail.name
            record.housing_status = detail.housing_status
            if detail.building_type:
                record.building_type = detail.building_type
            if detail.purpose:
                record.purpose = detail.purpose
            if detail.land_division:
                record.land_division = detail.land_division
            if detail.region_name:
                record.region_name = detail.region_name
            if detail.section_name:
                record.section_name = detail.section_name
            if detail.address:
                record.address = detail.address
            if detail.handover_time:
                record.handover_time = detail.handover_time
            if detail.open_sell_date:
                record.open_sell_date = detail.open_sell_date

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
            if detail.min_area_pin is not None:
                record.min_area_pin = detail.min_area_pin
            if detail.max_area_pin is not None:
                record.max_area_pin = detail.max_area_pin
            if detail.cover_image_url:
                record.cover_image_url = detail.cover_image_url
            if detail.image_urls:
                record.image_urls = detail.image_urls
            if detail.url:
                record.url = detail.url

            # 車位規格更新
            if detail.parking:
                if detail.parking.min_parking_price_wan is not None:
                    record.min_parking_price_wan = detail.parking.min_parking_price_wan
                if detail.parking.max_parking_price_wan is not None:
                    record.max_parking_price_wan = detail.parking.max_parking_price_wan
                if detail.parking.parking_ratio_desc:
                    record.parking_ratio_desc = detail.parking.parking_ratio_desc
                if detail.parking.parking_ratio is not None:
                    record.parking_ratio = detail.parking.parking_ratio
                if detail.parking.parking_planning_desc:
                    record.parking_planning_desc = detail.parking.parking_planning_desc
                if detail.parking.plane_parking_count is not None:
                    record.plane_parking_count = detail.parking.plane_parking_count
                if detail.parking.mechanical_parking_count is not None:
                    record.mechanical_parking_count = detail.parking.mechanical_parking_count
                if detail.parking.charging_piles_desc:
                    record.charging_piles_desc = detail.parking.charging_piles_desc
                if detail.parking.has_charging_piles is not None:
                    record.has_charging_piles = detail.parking.has_charging_piles
                if detail.parking.parking_type:
                    record.parking_type = detail.parking.parking_type

            # 結構化房型
            if layouts_dump is not None:
                record.layouts = layouts_dump

            # 描述與團隊更新
            if detail.structure:
                record.structure = detail.structure
            if detail.orientation:
                record.orientation = detail.orientation
            if detail.developer_company:
                record.developer_company = detail.developer_company
            if detail.builder_company:
                record.builder_company = detail.builder_company
            if detail.architect_company:
                record.architect_company = detail.architect_company
            if detail.sales_agency_company:
                record.sales_agency_company = detail.sales_agency_company
            if detail.reception_address:
                record.reception_address = detail.reception_address

            # 社區關聯與坐標更新
            if detail.community_uuid:
                record.community_uuid = detail.community_uuid
            if detail.external_community_id:
                record.external_community_id = detail.external_community_id
            if detail.community_name:
                record.community_name = detail.community_name
            if detail.community_age is not None:
                record.community_age = detail.community_age
            if detail.lat is not None:
                record.lat = detail.lat
            if detail.lng is not None:
                record.lng = detail.lng

        await self.session.flush()
        return record

    async def get_by_id(self, new_house_id: str) -> Optional[NewHouseTable]:
        """根據內部主鍵 ID 查詢新建案"""
        stmt = select(NewHouseTable).where(NewHouseTable.id == new_house_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_external_id(
        self, provider_id: str, external_project_id: str
    ) -> Optional[NewHouseTable]:
        """根據來源建案外部專案 ID 查詢新建案"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.external_project_id == external_project_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_external_community_id(
        self, provider_id: str, external_community_id: str
    ) -> List[NewHouseTable]:
        """根據外部關聯社區代碼反查其關聯之新建案清單"""
        stmt = select(NewHouseTable).where(
            NewHouseTable.provider_id == provider_id,
            NewHouseTable.external_community_id == external_community_id,
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

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
            stmt = stmt.where(NewHouseTable.region_name == region)
        if section:
            stmt = stmt.where(NewHouseTable.section_name == section)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    NewHouseTable.name.ilike(pattern),
                    NewHouseTable.address.ilike(pattern),
                    NewHouseTable.developer_company.ilike(pattern),
                )
            )

        stmt = stmt.order_by(NewHouseTable.updated_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
