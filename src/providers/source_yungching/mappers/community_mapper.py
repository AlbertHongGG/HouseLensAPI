"""HouseLensAPI - 永慶房屋社區資料模型正規化轉換器 (Yungching Community Mapper)

嚴格落實兩層式權威單一事實來源 (Two-Tier SSOT)：
- 清單 API：專責提取 7 大最小必要資訊 (ID, Name, Address, Lat, Lng, UnitPrice, Cover)。
- 詳情 API：剩下的 12 大主檔與硬體規格欄位 100% 在此取得 (County, District, BuildAge, TotalHouse, Arc...)。
- 客觀無資料：17 大欄位 100% 乾淨傳入 None (入庫為 SQL NULL)。
"""

import re
from typing import Any, Dict, List, Optional

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_yungching.mappers.photos_dto import (
    SourceYungchingPhotosDTO,
    normalize_yungching_image_url,
)


def _clean_str(val: Any) -> Optional[str]:
    """清洗字串，空值或全空白傳回 None"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _parse_float(val: Any) -> Optional[float]:
    """安全解析浮點數"""
    if val is None:
        return None
    try:
        # 去除文字單位干擾 (例如 "8.0年", "91.4萬/坪")
        cleaned = re.sub(r"[^\d.]", "", str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _parse_int(val: Any) -> Optional[int]:
    """安全解析整數"""
    if val is None:
        return None
    try:
        cleaned = re.sub(r"[^\d]", "", str(val))
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _normalize_region_name(raw_region: Optional[str]) -> Optional[str]:
    """正規化縣市名稱，統一將「臺」替換為「台」"""
    if not raw_region:
        return None
    norm = raw_region.strip().replace("臺", "台")
    return norm if norm else None


def _parse_facilities(val: Any) -> List[str]:
    """從公設描述字串中正則萃取清潔的公共設施清單"""
    if not val or not isinstance(val, str):
        return []

    text = val.strip()
    # 優先檢索括號內之公設列舉，例如: (健身房、交誼廳、兒童遊戲室、多功能空間、視聽影音室等..)
    bracket_match = re.search(r"[（\(](.*?)[）\)]", text)
    if bracket_match:
        target_str = bracket_match.group(1)
    else:
        target_str = text

    # 以頓號、逗號、分號分割
    tokens = re.split(r"[、,，;；\n]+", target_str)
    facilities: List[str] = []
    seen = set()

    for tok in tokens:
        item = tok.strip()
        # 清除結尾的 "等"、".."、"." 等贅字
        item = re.sub(r"(等|\.+|…+)+$", "", item).strip()
        if item and len(item) <= 30 and item not in seen:
            facilities.append(item)
            seen.add(item)

    return facilities


def map_yungching_community_summary(raw_item: Dict[str, Any]) -> NormalizedCommunitySummary:
    """將永慶房屋清單項目轉換為標準 NormalizedCommunitySummary (最小必要資訊)

    權威歸屬：
    - external_community_id: 100% 取自清單 ID
    - community_name: 100% 取自清單 Name
    - address: 100% 取自清單 Address
    - coordinates: 100% 取自清單 Lat / Lng
    - avg_unit_price_wan: 100% 取自清單 UnitPrice
    - cover_image_url: 100% 取自清單 Cover (轉換為 1200x900)
    """
    lat = _parse_float(raw_item.get("Lat"))
    lng = _parse_float(raw_item.get("Lng"))
    coords = GeoPoint(lat=lat, lng=lng) if lat is not None and lng is not None else None

    cover = normalize_yungching_image_url(raw_item.get("Cover"))

    return NormalizedCommunitySummary(
        provider_id="yungching",
        external_community_id=str(raw_item.get("ID")),
        community_name=str(raw_item.get("Name") or "").strip(),
        region_name="",
        section_name="",
        address=str(raw_item.get("Address") or "").strip(),
        coordinates=coords,
        avg_unit_price_wan=_parse_float(raw_item.get("UnitPrice")),
        cover_image_url=cover,
        building_type=None,
        purpose=None,
        housing_status=None,
        shopping_district=None,
        transport=None,
    )


def map_yungching_community_detail(
    summary: NormalizedCommunitySummary,
    raw_detail: Dict[str, Any],
) -> NormalizedCommunityDetail:
    """將永慶房屋封包組裝為強型別 NormalizedCommunityDetail

    職責邊界：
    - 最小必要資訊：100% 取自 summary。
    - 剩下的主檔屬性：100% 取自詳情 API (County, District, BuildAge, TotalHouse, Arc, BuildingCompany, PublicFacility, Pictures...)。
    - 客觀無資料：17 項客觀無資料欄位全部傳入 None (入庫為 SQL NULL)。
    """
    detail_data = raw_detail.get("Data") if isinstance(raw_detail.get("Data"), dict) else raw_detail

    # 詳情 API 權威取得之行政區域
    region_name = _normalize_region_name(detail_data.get("County"))
    section_name = _clean_str(detail_data.get("District"))

    # 詳情 API 權威取得之建築規格
    building_age = _parse_float(detail_data.get("BuildAge"))
    total_households = _parse_int(detail_data.get("TotalHouse"))
    floor_plan = _clean_str(detail_data.get("TotalFloor"))
    structure = _clean_str(detail_data.get("Arc"))
    developer_company = _clean_str(detail_data.get("BuildingCompany"))

    # 詳情 API 權威取得之公設與團隊
    intro_info = detail_data.get("IntroductionInfo") or {}
    public_facility_raw = intro_info.get("PublicFacility") if isinstance(intro_info, dict) else None
    facilities = _parse_facilities(public_facility_raw)
    transport = _clean_str(detail_data.get("LifeMapMrt"))
    architect_company = _clean_str(detail_data.get("ArcDesign"))

    # 詳情 API 權威取得之相簿與官方連結
    photos_dto = SourceYungchingPhotosDTO(detail_data)
    image_urls = photos_dto.image_urls
    share_link = _clean_str(detail_data.get("ShareLink"))

    # 封面圖片：優先保留清單已解析之封面，若無則由相簿封面回填
    cover_image = summary.cover_image_url or photos_dto.cover_url

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
        structure=structure,
        developer_company=developer_company,
        facilities=facilities,
        transport=transport,
        architect_company=architect_company,
        image_urls=image_urls,
        url=share_link,
        # --- 第三類：客觀無資料 (100% 權威正規化為 SQL NULL) ---
        building_type=None,
        purpose=None,
        housing_status=None,
        base_area_pin=None,
        public_ratio_pct=None,
        parking_count=None,
        parking_ratio=None,
        min_parking_price_wan=None,
        max_parking_price_wan=None,
        parking_type=None,
        manage_fee_per_pin=None,
        shopping_district=None,
        land_division=None,
        orientation=None,
        landscape_designer=None,
        public_facility_designer=None,
        builder_company=None,
    )
