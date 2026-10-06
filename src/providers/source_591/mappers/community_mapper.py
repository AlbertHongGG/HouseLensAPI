"""HouseLensAPI - 591 社區資料模型正規化轉換器 (591 Community Mapper)

將原始 591 社區封包在模組內部完全清洗，直接輸出 NormalizedCommunitySummary 與 NormalizedCommunityDetail。
"""

from typing import Any, Dict, List, Optional

from src.domain.common import GeoPoint
from src.domain.community import (
    NormalizedCommunityDetail,
    NormalizedCommunitySummary,
)
from src.providers.source_591.mappers.age_mapper import Source591AgeMapper
from src.providers.source_591.normalizers import (
    clean_optional_str,
    clean_parking_count,
    parse_currency_amount,
    parse_int_count,
    parse_parking_price_range,
    parse_percent,
    parse_pin,
    parse_unit_price,
)


class Source591CommunityPhotosDTO:
    """591 社區相簿防腐資料傳輸物件 (ACL DTO)

    專屬處理 /v1/app/gateway/community/info 回應中之 data.banners.community_images：
    - 大類巡訪：優先檢索 type == 'all'（全部圖片），相容遍歷各分組圖片
    - 排序保證：標記為 type == 'logo'（封面）的第一張相片強制置頂至第一順位 (index 0)
    - 畫質選取：優先選取 maxphoto (900px/1200px 高畫質水印大圖)，其次 bigphoto，再其次 photo
    - 去重與去雜：排除 is_video == 1，URL 去除重複並保證既有順序
    - 防腐解包：支援外層傳入完整 response、data 字典或 banners 字典
    """

    def __init__(self, raw: Optional[Any] = None):
        if isinstance(raw, list):
            self._banners = {"community_images": raw}
        elif isinstance(raw, dict):
            if "data" in raw and isinstance(raw["data"], dict):
                inner = raw["data"]
            else:
                inner = raw

            if "banners" in inner and isinstance(inner["banners"], dict):
                self._banners = inner["banners"]
            else:
                self._banners = inner
        else:
            self._banners = {}

    @property
    def cover_url(self) -> Optional[str]:
        """傳回封面高畫質照片 URL (若無標記封面則傳回第一張相片)"""
        urls = self.image_urls
        return urls[0] if urls else None

    @property
    def image_urls(self) -> List[str]:
        """傳回標準按序排列的高畫質照片 URL 列表 (封面保證置頂)"""
        community_images = self._banners.get("community_images")
        if not isinstance(community_images, list):
            return []

        cover_urls: List[str] = []
        regular_urls: List[str] = []
        seen: set = set()

        # 1. 尋找 type == 'all' 的大類群組
        all_group = None
        for grp in community_images:
            if isinstance(grp, dict) and grp.get("type") == "all":
                all_group = grp
                break

        if all_group:
            target_subgroups = all_group.get("images") or all_group.get("list") or []
        else:
            target_subgroups = community_images

        # 2. 遍歷相片並萃取（支援階層子群組或直接相片項目）
        for item in target_subgroups:
            if not isinstance(item, dict):
                continue

            sub_imgs = item.get("images") or item.get("list")
            is_logo_subgroup = item.get("type") == "logo"

            if isinstance(sub_imgs, list):
                photos_to_process = [(img, is_logo_subgroup) for img in sub_imgs if isinstance(img, dict)]
            else:
                photos_to_process = [(item, is_logo_subgroup)]

            for img, is_logo in photos_to_process:
                # 排除影片
                if str(img.get("is_video")) in ("1", "true", "True"):
                    continue

                # 優先提取最高畫質: maxphoto > bigphoto > photo
                raw_url = (
                    img.get("maxphoto")
                    or img.get("bigphoto")
                    or img.get("photo")
                    or img.get("smallphoto")
                )
                if not raw_url or not str(raw_url).strip():
                    continue

                url = str(raw_url).strip()
                if url in seen:
                    continue
                seen.add(url)

                if is_logo:
                    cover_urls.append(url)
                else:
                    regular_urls.append(url)

        return cover_urls + regular_urls



def map_community_summary(item: Dict[str, Any]) -> NormalizedCommunitySummary:
    """將 591 search/list 原始項目轉換為標準 NormalizedCommunitySummary (基礎識別與地理唯一來源)"""
    # 座標解析 (唯一正規來源：清單 API)
    lat = item.get("lat")
    lng = item.get("lng")
    coords: Optional[GeoPoint] = None
    if lat and lng:
        try:
            coords = GeoPoint(lat=float(lat), lng=float(lng))
        except (ValueError, TypeError):
            coords = None

    # 單價數值化解析
    price_obj = item.get("price") or {}
    avg_price: Optional[float] = None
    if isinstance(price_obj, dict):
        avg_price = parse_unit_price(price_obj.get("price"))

    # 封面圖解析 (唯一正規來源：清單 API)
    photo_obj = item.get("photo_src") or {}
    cover_url: Optional[str] = None
    if isinstance(photo_obj, dict):
        cover_url = clean_optional_str(photo_obj.get("src"))
    elif isinstance(photo_obj, str):
        cover_url = clean_optional_str(photo_obj)

    region = str(item.get("region") or "").strip()
    section = str(item.get("section") or "").strip()
    simple_addr = str(item.get("simple_address") or "").strip()
    full_addr = f"{region}{section}{simple_addr}"

    return NormalizedCommunitySummary(
        provider_id="591",
        external_community_id=str(item.get("id")),
        community_name=str(item.get("name") or "").strip(),
        region_name=region,
        section_name=section,
        address=full_addr,
        coordinates=coords,
        avg_unit_price_wan=avg_price,
        building_type=None,
        purpose=clean_optional_str(item.get("build_purpose_simple")),
        housing_status=clean_optional_str(item.get("housing_text")),
        shopping_district=clean_optional_str(item.get("shop_name")),
        transport=clean_optional_str(item.get("station_name")),
        cover_image_url=cover_url,
    )


def map_community_detail(
    summary: NormalizedCommunitySummary,
    data: Dict[str, Any],
) -> NormalizedCommunityDetail:
    """將 591 社區封包組裝為強型別 NormalizedCommunityDetail。

    職責邊界：
    - 基礎身分與地理資訊：100% 來自清單 API (summary)。
    - 建築規劃與深層規格：100% 來自詳情 API build_info 單一區塊，絕不跨區塊抓取。
    """
    build_info = data.get("build_info") or {}

    # 屋齡解析為浮點數
    age_obj = build_info.get("age")
    age_raw = age_obj.get("content") if isinstance(age_obj, dict) else (str(age_obj) if age_obj else None)
    building_age = Source591AgeMapper.parse_building_age(age_raw)

    # 總戶數與車位數純整數解析
    house_num_obj = build_info.get("all_house_num")
    house_raw = house_num_obj.get("content") if isinstance(house_num_obj, dict) else (str(house_num_obj) if house_num_obj else None)
    total_households = parse_int_count(house_raw)

    park_num_raw = build_info.get("all_park_num")
    park_raw = build_info.get("park")
    park_rate_raw = build_info.get("park_rate")
    parking_count = clean_parking_count(
        count_raw=park_num_raw,
        park_raw=park_raw,
        rate_raw=park_rate_raw,
    )

    # 車位價格純數值解析 (min_parking_price_wan, max_parking_price_wan)
    min_park_price, max_park_price = parse_parking_price_range(build_info.get("park_price"))

    # 車位型態空值純化
    parking_type = clean_optional_str(build_info.get("park_type_str"))

    # 車位配比與公設比解析
    park_ratio = None
    if park_rate_raw and ":" in str(park_rate_raw):
        try:
            parts = str(park_rate_raw).split(":")
            park_ratio = float(parts[1].strip())
        except (ValueError, IndexError):
            park_ratio = None
    elif park_rate_raw:
        park_ratio = parse_unit_price(park_rate_raw)

    public_ratio = parse_percent(build_info.get("ratio"))

    # 管理費單價純整數 (元/坪/月)
    manage_obj = build_info.get("manage_cost")
    manage_raw = manage_obj.get("price") if isinstance(manage_obj, dict) else (str(manage_obj) if manage_obj else None)
    manage_fee = parse_currency_amount(manage_raw)

    # 基地面積純浮點數 (坪)
    base_area_pin = parse_pin(build_info.get("base_area_num"))

    # 土地使用分區
    land_division = clean_optional_str(build_info.get("land_division"))

    # 三維正交解耦映射 (直取 build_info 單一區塊)
    # 1. 建物實體型態 (如: 住宅大樓、華廈、透天、商辦)
    building_type = clean_optional_str(build_info.get("purpose_str"))

    # 2. 法定使用用途 (100% 來自詳情 build_info.purpose_other2)
    purpose = clean_optional_str(build_info.get("purpose_other2"))

    # 3. 成屋/建案狀態 (100% 來自詳情 build_info.build_type / build_type_str)
    raw_status_code = build_info.get("build_type")
    raw_status_str = clean_optional_str(build_info.get("build_type_str"))
    if raw_status_str:
        housing_status = raw_status_str
    elif raw_status_code == 1:
        housing_status = "預售屋"
    elif raw_status_code == 2:
        housing_status = "新成屋"
    elif raw_status_code == 5:
        housing_status = "中古屋"
    else:
        housing_status = None

    # 公設清單
    facility_raw = build_info.get("facility") or []
    facility_list = []
    if isinstance(facility_raw, str):
        facility_list = [f.strip() for f in facility_raw.split(",") if f.strip()]
    elif isinstance(facility_raw, list):
        facility_list = [str(f).strip() for f in facility_raw if clean_optional_str(f)]

    # 社區原始網址 (100% 取自 share_info.url)
    share_info = data.get("share_info") or {}
    community_url = clean_optional_str(share_info.get("url"))

    # 社區相簿圖片清單防腐整合 (取自 data.banners.community_images)
    photos_dto = Source591CommunityPhotosDTO(data)
    image_urls = photos_dto.image_urls

    # 高畫質封面圖：若清單已有封面則保留，若清單無封面則由相簿封面回填
    cover_image = summary.cover_image_url or photos_dto.cover_url

    return NormalizedCommunityDetail(
        # --- 基礎識別、地理資訊與市場行情：100% 取自清單 (summary，成交均價單一事實來源) ---
        provider_id=summary.provider_id,
        external_community_id=summary.external_community_id,
        community_name=summary.community_name,
        region_name=summary.region_name,
        section_name=summary.section_name,
        address=summary.address,
        coordinates=summary.coordinates,
        avg_unit_price_wan=summary.avg_unit_price_wan,
        cover_image_url=cover_image,
        image_urls=image_urls,
        url=community_url,
        shopping_district=summary.shopping_district,
        transport=summary.transport,
        # --- 建築規格與規劃：100% 取自詳情 build_info 單一區塊 (三維解耦) ---
        building_type=building_type,
        purpose=purpose,
        housing_status=housing_status,
        total_households=total_households,
        parking_count=parking_count,
        min_parking_price_wan=min_park_price,
        max_parking_price_wan=max_park_price,
        parking_type=parking_type,
        parking_ratio=park_ratio,
        public_ratio_pct=public_ratio,
        manage_fee_per_pin=manage_fee,
        base_area_pin=base_area_pin,
        land_division=land_division,
        building_age_years=building_age,
        structure=clean_optional_str(build_info.get("structural_engine")),
        orientation=clean_optional_str(build_info.get("direction_rule")),
        floor_plan=clean_optional_str(build_info.get("floor")),
        facilities=facility_list,
        developer_company=clean_optional_str(build_info.get("company")),
        builder_company=clean_optional_str(build_info.get("build_company")),
        architect_company=clean_optional_str(build_info.get("construction_company")),
        landscape_designer=clean_optional_str(build_info.get("landscape_name")),
        public_facility_designer=clean_optional_str(build_info.get("postulate_name")),
    )

