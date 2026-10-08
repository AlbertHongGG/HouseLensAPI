"""HouseLensAPI - 信義房屋社區領域模型映射裝配器 (Sinyi Community Mapper)

嚴格落實 Two-Tier SSOT 權威單一事實來源：
- 清單 API：專責提取 7 大最小必要資訊 (commId, commName, address, lat, lng, uniprice, image)。
- 詳情 API：剩下的 10 大主檔與硬體規格欄位 100% 在此取得 (cityName, zipName, age, houseCount, floorRange, publicpercent, buildingStructure, facilities, constructCompany, images)。
- 客觀無資料：17 大欄位 100% 乾淨傳入 None (入庫為 SQL NULL)。
"""

import logging
from typing import Any, Dict, Optional

from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_sinyi.normalizers import (
    clean_str,
    parse_coordinates,
    parse_facilities,
    parse_float,
    parse_image_urls,
    parse_int,
    parse_public_ratio,
)

logger = logging.getLogger(__name__)


def map_sinyi_community_list_item(raw_item: Dict[str, Any]) -> NormalizedCommunitySummary:
    """將信義房屋網頁端清單項目轉換為標準 NormalizedCommunitySummary (最小必要資訊)

    權威歸屬：
    - external_community_id: 100% 取自清單 commId
    - community_name: 100% 取自清單 commName
    - address: 100% 取自清單 address
    - coordinates: 100% 取自清單 latitude / longitude
    - avg_unit_price_wan: 100% 取自清單 uniprice (成交均價)
    - cover_image_url: 100% 取自清單 image
    - building_age_years: 100% 取自清單 age
    """
    comm_id = str(raw_item.get("commId", "")).strip()
    name = str(raw_item.get("commName", "")).strip()
    addr = str(raw_item.get("address", "")).strip()

    coords = parse_coordinates(raw_item.get("latitude"), raw_item.get("longitude"))
    unit_price = parse_float(raw_item.get("uniprice"))
    age = parse_float(raw_item.get("age"))
    cover = clean_str(raw_item.get("image"))

    url = f"https://www.sinyi.com.tw/community/{comm_id}" if comm_id else None

    return NormalizedCommunitySummary(
        provider_id="sinyi",
        external_community_id=comm_id,
        community_name=name,
        region_name="",
        section_name="",
        address=addr,
        coordinates=coords,
        avg_unit_price_wan=unit_price,
        building_age_years=age,
        cover_image_url=cover,
        url=url,
        building_type=None,
        purpose=None,
        housing_status=None,
        shopping_district=None,
        transport=None,
    )


def map_sinyi_community_detail(
    raw_detail: Dict[str, Any],
    summary: Optional[NormalizedCommunitySummary] = None,
) -> NormalizedCommunityDetail:
    """將信義房屋封包組裝為強型別 NormalizedCommunityDetail

    職責邊界：
    - 最小必要資訊：100% 取自 summary (若 summary 為 None，從 detail 兜底提取)。
    - 剩下的主檔屬性：100% 取自詳情 API (cityName, zipName, age, houseCount, floorRange, publicpercent, buildingStructure, facilities, constructCompany, images)。
    - 客觀無資料：17 項客觀無資料欄位全部傳入 None (入庫為 SQL NULL)。
    """
    content = raw_detail.get("content") if isinstance(raw_detail.get("content"), dict) else raw_detail

    # 若未提供 summary (例如單純依外部 ID 直接查詢)，從 detail 的基礎同名欄位建立兜底最小必要 summary
    if summary is None:
        comm_id = str(content.get("commId", "")).strip()
        name = str(content.get("name") or content.get("commName") or "").strip()
        addr = str(content.get("address") or content.get("addr") or "").strip()
        coords = parse_coordinates(content.get("latitude"), content.get("longitude"))
        images_list = parse_image_urls(content.get("images"))
        cover = images_list[0] if images_list else None
        age = parse_float(content.get("age"))

        summary = NormalizedCommunitySummary(
            provider_id="sinyi",
            external_community_id=comm_id,
            community_name=name,
            region_name=clean_str(content.get("cityName")) or "",
            section_name=clean_str(content.get("zipName")) or "",
            address=addr,
            coordinates=coords,
            avg_unit_price_wan=None,  # 詳情 API 客觀無均價
            building_age_years=age,
            cover_image_url=cover,
            url=f"https://www.sinyi.com.tw/community/{comm_id}" if comm_id else None,
            building_type=None,
            purpose=None,
            housing_status=None,
            shopping_district=None,
            transport=None,
        )

    # 詳情 API 權威取得之行政區域名稱 (NormalizedCommunityDetail 規範為必填 str，None 則保底為 "")
    region_name = clean_str(content.get("cityName")) or ""
    section_name = clean_str(content.get("zipName")) or ""

    # 詳情 API 權威取得之建築規格
    building_age = parse_float(content.get("age"))
    total_households = parse_int(content.get("houseCount"))
    floor_plan = clean_str(content.get("floorRange") or content.get("floors"))
    public_ratio = parse_public_ratio(content.get("publicpercent"))
    structure = clean_str(content.get("buildingStructure"))

    # 詳情 API 權威取得之公設與團隊
    facilities = parse_facilities(content.get("publicDesc"))
    developer_company = clean_str(content.get("constructCompany") or content.get("builder"))

    # 詳情 API 權威取得之相簿與官方連結
    images = parse_image_urls(content.get("images"))
    cover_image = summary.cover_image_url or (images[0] if images else None)
    share_url = clean_str(content.get("shareURL")) or f"https://www.sinyi.com.tw/community/{summary.external_community_id}"

    return NormalizedCommunityDetail(
        # --- 第一層：清單 API 權威取得之最小必要資訊 (來自 summary) ---
        provider_id=summary.provider_id,
        external_community_id=summary.external_community_id,
        community_name=summary.community_name,
        address=summary.address,
        coordinates=summary.coordinates,
        avg_unit_price_wan=summary.avg_unit_price_wan,
        cover_image_url=cover_image,
        # --- 第二層：詳情 API 權威取得之剩下主檔屬性 ---
        region_name=region_name,
        section_name=section_name,
        building_age_years=building_age,
        total_households=total_households,
        floor_plan=floor_plan,
        public_ratio_pct=public_ratio,
        structure=structure,
        facilities=facilities,
        developer_company=developer_company,
        image_urls=images,
        url=share_url,
        # --- 第三類：客觀無資料 (100% 權威正規化為 SQL NULL) ---
        building_type=None,
        purpose=None,
        housing_status=None,
        base_area_pin=None,
        parking_count=None,
        parking_ratio=None,
        min_parking_price_wan=None,
        max_parking_price_wan=None,
        manage_fee_per_pin=None,
        shopping_district=None,
        transport=None,
        parking_type=None,
        land_division=None,
        orientation=None,
        landscape_designer=None,
        public_facility_designer=None,
        builder_company=None,
        architect_company=None,
    )
