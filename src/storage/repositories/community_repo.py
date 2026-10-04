"""HouseLensAPI - 社區資料庫倉儲實作 (Community Repository Implementation)

純數值與純強型別入庫：零字串正則解析、零未清洗雜質！
"""

import uuid
from typing import List, Optional, Set
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.storage.interfaces import ICommunityRepository
from src.storage.models.community import CommunityTable


class CommunityRepository(ICommunityRepository):
    """SQLAlchemy 2.0 非同步社區倉儲實作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def filter_existing_external_ids(
        self, provider_id: str, external_ids: List[str]
    ) -> Set[str]:
        """批次查詢傳入的外部社區 ID 中已存在於資料庫者"""
        if not external_ids:
            return set()
        stmt = select(CommunityTable.source_id).where(
            CommunityTable.source_provider == provider_id,
            CommunityTable.source_id.in_(external_ids),
        )
        res = await self.session.execute(stmt)
        return set(res.scalars().all())

    async def upsert_from_summary(
        self, summary: NormalizedCommunitySummary, provider_id: str
    ) -> CommunityTable:
        """從 NormalizedCommunitySummary 新增或更新社區節點"""
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
                build_purpose=summary.build_purpose,
                build_type=summary.building_type,
                region_name=summary.region_name,
                section_name=summary.section_name,
                address=summary.address,
                lat=lat,
                lng=lng,
                avg_unit_price_wan=summary.avg_unit_price_wan,
                building_age_years=summary.building_age_years,
                shopping_district=summary.shopping_district,
                transport=summary.transport,
                cover_image_url=summary.cover_image_url,
            )
            self.session.add(record)
        else:
            record.name = summary.community_name
            if summary.build_purpose:
                record.build_purpose = summary.build_purpose
            if summary.building_type:
                record.build_type = summary.building_type
            if summary.region_name:
                record.region_name = summary.region_name
            if summary.section_name:
                record.section_name = summary.section_name
            if summary.address:
                record.address = summary.address
            if lat is not None and lng is not None:
                record.lat = lat
                record.lng = lng
            if summary.avg_unit_price_wan is not None:
                record.avg_unit_price_wan = summary.avg_unit_price_wan
            if summary.building_age_years is not None:
                record.building_age_years = summary.building_age_years
            if summary.shopping_district:
                record.shopping_district = summary.shopping_district
            if summary.transport:
                record.transport = summary.transport
            if summary.cover_image_url:
                record.cover_image_url = summary.cover_image_url

        await self.session.flush()
        return record

    async def upsert_from_detail(
        self, detail: NormalizedCommunityDetail, provider_id: str
    ) -> CommunityTable:
        """從 NormalizedCommunityDetail 新增或更新社區完整規格"""
        stmt = select(CommunityTable).where(
            CommunityTable.source_provider == provider_id,
            CommunityTable.source_id == detail.community_id,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        lat = detail.coordinates.lat if detail.coordinates else None
        lng = detail.coordinates.lng if detail.coordinates else None

        if record is None:
            record = CommunityTable(
                id=str(uuid.uuid4()),
                source_provider=provider_id,
                source_id=detail.community_id,
                name=detail.community_name,
                build_type=detail.building_type,
                build_purpose=detail.build_purpose,
                transport=detail.transport,
                address=detail.address,
                region_name=detail.region_name,
                section_name=detail.section_name,
                shopping_district=detail.shopping_district,
                lat=lat,
                lng=lng,
                avg_unit_price_wan=detail.avg_unit_price_wan,
                building_age_years=detail.building_age_years,
                total_households=detail.total_households,
                base_area_pin=detail.base_area_pin,
                public_ratio_pct=detail.public_ratio_pct,
                parking_count=detail.parking_count,
                parking_ratio_pct=detail.parking_ratio_pct,
                manage_fee_per_pin=detail.manage_fee_per_pin,
                floor_plan=detail.floor_plan,
                structure=detail.structure,
                park_type_str=detail.park_type_str,
                park_price=detail.park_price,
                land_division=detail.land_division,
                direction_rule=detail.direction_rule,
                landscape_name=detail.landscape_name,
                postulate_name=detail.postulate_name,
                facilities=detail.facilities,
                developer_company=detail.developer_company,
                builder_company=detail.builder_company,
                architect_company=detail.architect_company,
                cover_image_url=detail.cover_image_url,
                base_area_num=detail.base_area_num,
            )
            self.session.add(record)
        else:
            record.name = detail.community_name
            if detail.building_type:
                record.build_type = detail.building_type
            if detail.build_purpose:
                record.build_purpose = detail.build_purpose
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
            if lat is not None and lng is not None:
                record.lat = lat
                record.lng = lng

            # 數值更新
            if detail.avg_unit_price_wan is not None:
                record.avg_unit_price_wan = detail.avg_unit_price_wan
            if detail.building_age_years is not None:
                record.building_age_years = detail.building_age_years
            if detail.total_households is not None:
                record.total_households = detail.total_households
            if detail.base_area_num is not None:
                record.base_area_num = detail.base_area_num
                record.base_area_pin = detail.base_area_num
            elif detail.base_area_pin is not None:
                record.base_area_pin = detail.base_area_pin
                record.base_area_num = detail.base_area_pin
            if detail.public_ratio_pct is not None:
                record.public_ratio_pct = detail.public_ratio_pct
            if detail.parking_count is not None:
                record.parking_count = detail.parking_count
            if detail.parking_ratio_pct is not None:
                record.parking_ratio_pct = detail.parking_ratio_pct
            if detail.manage_fee_per_pin is not None:
                record.manage_fee_per_pin = detail.manage_fee_per_pin

            # 描述更新
            if detail.floor_plan:
                record.floor_plan = detail.floor_plan
            if detail.structure:
                record.structure = detail.structure
            if detail.park_type_str:
                record.park_type_str = detail.park_type_str
            if detail.park_price:
                record.park_price = detail.park_price
            if detail.land_division:
                record.land_division = detail.land_division
            if detail.direction_rule:
                record.direction_rule = detail.direction_rule
            if detail.landscape_name:
                record.landscape_name = detail.landscape_name
            if detail.postulate_name:
                record.postulate_name = detail.postulate_name
            if detail.facilities:
                record.facilities = detail.facilities
            if detail.developer_company:
                record.developer_company = detail.developer_company
            if detail.builder_company:
                record.builder_company = detail.builder_company
            if detail.architect_company:
                record.architect_company = detail.architect_company
            if detail.cover_image_url:
                record.cover_image_url = detail.cover_image_url

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
        min_age_years: Optional[float] = None,
        max_age_years: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityTable]:
        """多條件檢索庫存社區 (含屋齡篩選)"""
        stmt = select(CommunityTable)
        if region:
            stmt = stmt.where(CommunityTable.region_name == region)
        if section:
            stmt = stmt.where(CommunityTable.section_name == section)
        if min_age_years is not None:
            stmt = stmt.where(CommunityTable.building_age_years >= min_age_years)
        if max_age_years is not None:
            stmt = stmt.where(CommunityTable.building_age_years <= max_age_years)
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
