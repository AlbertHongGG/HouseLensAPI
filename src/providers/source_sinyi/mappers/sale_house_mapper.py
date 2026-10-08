"""HouseLensAPI - 信義房屋中古屋領域模型映射裝配器 (Sinyi Sale House Mapper)

負責將信義房屋手機端原始封包資料裝配為跨來源統一之標準領域模型：
- 清單項目 (NormalizedSaleListing) 100% 自清單 API (/filterObject.php) 提取。
- 實體詳情 (NormalizedSalePropertyDetail) 100% 自詳情 API (/getObjectContent.php) 提取。
- 客觀無資料欄位 100% 純化為 None (SQL NULL)。
"""

import logging
from typing import Any, Dict, Optional

from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_sinyi.normalizers import (
    normalize_orientation,
    parse_address,
    parse_age,
    parse_coordinates,
    parse_float,
    parse_floor,
    parse_image_urls,
    parse_int,
    parse_layout,
    parse_management_fee,
    parse_unit_price,
)

logger = logging.getLogger(__name__)


def map_sinyi_sale_house_list_item(obj: Dict[str, Any]) -> NormalizedSaleListing:
    """將清單 API (/filterObject.php) 的 object 元素轉換為標準刊登模型

    所有欄位 100% 來自清單 API，未提供者純化為 None。
    """
    house_no = str(obj.get("houseNo", "")).strip()
    name = str(obj.get("name", "")).strip()
    price = int(obj.get("price", 0))
    area_building = float(obj.get("areaBuilding", 0.0))

    floor_curr = parse_floor(obj.get("floor"))
    floor_tot = parse_int(obj.get("floors"))
    rooms, halls, baths = parse_layout(obj.get("layout") or obj.get("totalLayout"))
    age = parse_age(obj.get("age"))

    raw_addr = obj.get("address")
    region, section, street = parse_address(raw_addr)
    # 若地址未拆出縣市行政區，提供自衛預設
    region_val = region or "台北市"
    section_val = section or ""

    comm_id = str(obj.get("commId", "")).strip() or None
    cover_img = obj.get("largeImage") or obj.get("image") or None

    return NormalizedSaleListing(
        provider_id="sinyi",
        external_house_id=house_no,
        title=name,
        price_wan=price,
        unit_price_wan=None,  # 清單未提供結構化單價
        total_area_pin=area_building,
        floor_current=floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=halls,
        bathrooms=baths,
        building_age_years=age,
        building_type=None,  # 清單未提供建物型態
        is_whole_building=False,
        region_name=region_val,
        section_name=section_val,
        street=street,
        address=raw_addr,
        external_community_id=comm_id,
        community_name=None,  # 清單未提供社區名稱
        has_parking=bool(obj.get("isParking", False)),
        cover_image_url=cover_img,
        url=None,  # 清單未提供官方展示網址，固定為 None，由詳情提供
        raw_data=obj,
    )


def map_sinyi_sale_house_detail(content: Dict[str, Any]) -> NormalizedSalePropertyDetail:
    """將詳情 API (/getObjectContent.php) 的 content 字典轉換為完整實體規格模型

    所有規格 100% 來自詳情 API，客觀無數據者 100% 純化為 None (SQL NULL)。
    """
    house_no = str(content.get("houseNo", "")).strip()
    name = str(content.get("name", "")).strip()
    price = int(content.get("price", 0))
    unit_price = parse_unit_price(content.get("price_item"), content.get("rawUniPrice"))
    total_area = float(content.get("areaBuilding", 0.0))

    # 產權面積純浮點數拆解
    main_area = parse_float(content.get("mainBuilding"))
    ping_used = parse_float(content.get("pingUsed"))
    aux_area: Optional[float] = None
    balconies: Optional[int] = None
    if ping_used is not None and main_area is not None:
        diff = round(ping_used - main_area, 2)
        if diff > 0.0:
            aux_area = diff
            balconies = 1  # 陽台/附屬建物存在

    land_area = parse_float(content.get("areaLand"))

    # 格局與樓層
    rooms, halls, baths = parse_layout(content.get("layout") or content.get("totalLayout"))
    floor_curr = parse_floor(content.get("floor"))
    floor_tot = parse_int(content.get("floors"))
    age = parse_age(content.get("age"))

    # 管理費與型態
    mgmt_fee = parse_management_fee(content.get("monthlyFee"))
    b_type = content.get("type") or None
    is_whole = False
    if b_type:
        is_whole = any(k in b_type for k in ("透天", "別墅", "整棟"))

    orientation = normalize_orientation(content.get("houseFront"))
    parking_desc = content.get("parking") or None

    # 地址與經緯度
    raw_addr = content.get("address")
    region, section, street = parse_address(raw_addr)
    coords = parse_coordinates(content.get("latitude"), content.get("longitude"))

    # 社區關聯代碼與名稱
    comm_id = str(content.get("commId", "")).strip() or None
    comm_name = str(content.get("commName", "")).strip() or None

    # 高清圖庫與展示連結
    images = parse_image_urls(content.get("images"), content.get("layoutImage"))
    cover_img = images[0] if images else None
    share_url = content.get("shareURL") or None

    return NormalizedSalePropertyDetail(
        provider_id="sinyi",
        external_house_id=house_no,
        title=name,
        price_wan=price,
        unit_price_wan=unit_price,
        total_area_pin=total_area,
        # 產權面積純浮點數拆解
        main_area_pin=main_area,
        auxiliary_area_pin=aux_area,
        common_area_pin=None,  # 客觀無資料 -> 100% SQL NULL
        land_area_pin=land_area,
        parking_area_pin=None,  # 客觀無資料 -> 100% SQL NULL
        # 建築物理規格 (純數值)
        floor_current=floor_curr,
        floor_total=floor_tot,
        rooms=rooms,
        living_rooms=halls,
        bathrooms=baths,
        balconies=balconies,
        building_age_years=age,
        public_ratio_pct=None,  # 客觀無資料 -> 100% SQL NULL
        management_fee_monthly=mgmt_fee,
        has_lease=None,  # 客觀無資料 -> 100% SQL NULL
        # 構造與現況描述
        building_type=b_type,
        structure=None,  # 客觀無資料 -> 100% SQL NULL
        is_whole_building=is_whole,
        orientation=orientation,
        purpose=None,  # 客觀無資料 -> 100% SQL NULL
        current_state=None,  # 客觀無資料 -> 100% SQL NULL
        parking_desc=parking_desc,
        # 地理位置與結構化資訊
        region_name=region,
        section_name=section,
        street=street,
        address=raw_addr,
        coordinates=coords,
        external_community_id=comm_id,
        community_name=comm_name,
        cover_image_url=cover_img,
        image_urls=images,
        url=share_url,
    )
