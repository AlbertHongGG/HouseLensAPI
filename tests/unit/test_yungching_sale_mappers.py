"""HouseLensAPI - 永慶房屋中古屋資料模型正規化與相簿 DTO 單元測試套件

使用封包紀錄/yungching 底下真實 API 回應封包進行完整斷言驗證。
嚴格檢驗兩層式 SSOT 原則：
- price_wan（實體總價）與 unit_price_wan（實體單價）100% 取自詳情 API
- 產權五大面積、格局樓層、相簿與客觀為空欄位 (公設比、租約、現況為 None)
"""

import json
from pathlib import Path
import pytest

from src.core.interfaces.sale_house import ISaleHouseProvider
from src.core.registry import registry
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
)
from src.providers.source_yungching.mappers.photos_dto import (
    SourceYungchingSalePhotosDTO,
    normalize_yungching_image_url,
)
from src.providers.source_yungching.mappers.sale_house_mapper import (
    map_yungching_sale_detail,
    map_yungching_sale_listing,
)
from src.providers.source_yungching.sale_house import SourceYungchingSaleHouseProvider
import src.providers  # 確保 provider 註冊載入


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "封包紀錄" / "yungching"


def _load_fixture_json(filename: str) -> dict:
    filepath = FIXTURE_DIR / filename
    content = filepath.read_text(encoding="utf-8")
    json_start = content.find("{")
    if json_start != -1:
        content = content[json_start:]
    return json.loads(content)


def test_normalize_yungching_image_url_variants():
    """測試永慶圖片 CDN 與模板動態替換高畫質 (1200x900) 尺寸"""
    # 1. yccdn 網址替換 query string
    cdn_url = "https://yccdn.yungching.com.tw/Upload/Cases/YCBUD01/123.jpg?width=300&height=225"
    assert normalize_yungching_image_url(cdn_url) == (
        "https://yccdn.yungching.com.tw/Upload/Cases/YCBUD01/123.jpg?width=1200&height=900"
    )

    # 2. pic 網址模板替換
    pic_tpl = "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCHOUSE/photo1.jpg"
    assert normalize_yungching_image_url(pic_tpl) == (
        "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCHOUSE/photo1.jpg"
    )

    # 3. pic 網址指定尺寸替換
    pic_thumb = "https://pic.yungching.com.tw/res/DrawImage/ShowPic/300/225/YCHOUSE/photo1.jpg"
    assert normalize_yungching_image_url(pic_thumb) == (
        "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCHOUSE/photo1.jpg"
    )

    # 4. 空值與無效字串
    assert normalize_yungching_image_url(None) is None
    assert normalize_yungching_image_url("") is None


def test_source_yungching_sale_photos_dto():
    """測試中古屋相簿 DTO: 包含格局圖、相片清單、封面置頂與去重保序"""
    raw_payload = {
        "Cover": "https://yccdn.yungching.com.tw/Upload/Cases/YC/cover.jpg?width=300&height=225",
        "FloorPlan": "https://yccdn.yungching.com.tw/Upload/Cases/YC/floorplan.jpg?width=300&height=225",
        "PictureList": [
            "https://yccdn.yungching.com.tw/Upload/Cases/YC/pic1.jpg?width=300&height=225",
            "https://yccdn.yungching.com.tw/Upload/Cases/YC/cover.jpg?width=300&height=225",  # 重複封面
            "https://yccdn.yungching.com.tw/Upload/Cases/YC/pic2.jpg?width=300&height=225",
        ],
    }
    dto = SourceYungchingSalePhotosDTO(raw_payload)
    urls = dto.image_urls

    # 驗證總共有 4 張圖片 (cover, pic1, pic2, floorplan 去重後)
    assert len(urls) == 4
    # 封面強制置頂至第一順位且升級為 1200x900
    assert urls[0] == "https://yccdn.yungching.com.tw/Upload/Cases/YC/cover.jpg?width=1200&height=900"
    assert dto.cover_url == urls[0]
    # 格局圖亦升級並納入清單中
    assert "https://yccdn.yungching.com.tw/Upload/Cases/YC/floorplan.jpg?width=1200&height=900" in urls


def test_map_yungching_sale_listing_real_fixture():
    """使用真實房屋物件清單封包斷言刊登轉換與最小必要資訊"""
    data = _load_fixture_json("房屋物件清單 Respond.json")
    items_raw = data.get("Data", {}).get("ListObjects", [])
    assert len(items_raw) > 0

    first_item = items_raw[0]
    listing = map_yungching_sale_listing(first_item, query_region="台北市")

    assert isinstance(listing, NormalizedSaleListing)
    assert listing.provider_id == "yungching"
    # CaseID 作為 external_house_id
    assert listing.external_house_id == first_item.get("CaseID")
    assert listing.title == first_item.get("CaseName")
    assert listing.price_wan == 3699
    assert listing.total_area_pin == pytest.approx(67.6)
    assert listing.rooms == 3
    assert listing.living_rooms == 2
    assert listing.bathrooms == 2
    assert listing.building_age_years == pytest.approx(4.7)
    assert listing.region_name == "台北市"
    assert listing.address == "台北市北投區新民路"
    assert listing.url == f"https://buy.yungching.com.tw/house/{first_item.get('CaseID')}"
    assert listing.cover_image_url is not None


def test_map_yungching_sale_detail_real_fixture():
    """使用真實房屋物件詳情資訊封包驗證 SSOT 產權拆解、價格取值與客觀為空規範"""
    detail_data = _load_fixture_json("房屋物件詳情資訊 Respond.json")
    data_block = detail_data.get("Data", {})

    listing = map_yungching_sale_listing(data_block)
    detail = map_yungching_sale_detail(listing=listing, raw_detail=data_block)

    assert isinstance(detail, NormalizedSalePropertyDetail)
    assert detail.provider_id == "yungching"
    assert detail.external_house_id == "c7521dcc-3afc-4fcf-af68-57ef8bb8547c"

    # 1. SSOT 關鍵裁定驗證: price_wan 與 unit_price_wan 100% 來自詳情 API
    assert detail.price_wan == 4188
    assert detail.unit_price_wan == pytest.approx(100.2)

    # 2. 產權五大面積純數值拆解驗證 (RegisterInfo)
    assert detail.total_area_pin == pytest.approx(43.22)
    assert detail.main_area_pin == pytest.approx(20.75)
    assert detail.auxiliary_area_pin == pytest.approx(2.8)
    assert detail.common_area_pin == pytest.approx(19.69)
    assert detail.land_area_pin == pytest.approx(7.78)
    assert detail.parking_area_pin == pytest.approx(3.92)

    # 3. 格局與樓層驗證 (HouseInfo)
    assert detail.rooms == 3
    assert detail.living_rooms == 2
    assert detail.bathrooms == 2
    assert detail.floor_current == 4
    assert detail.floor_total == 11
    assert detail.building_age_years == pytest.approx(0.3)
    assert detail.orientation == "朝北"
    assert detail.parking_desc == "塔式車位"

    # 4. 客觀未提供欄位正規化為 None 驗證
    assert detail.public_ratio_pct is None
    assert detail.has_lease is None
    assert detail.current_state is None
    assert detail.management_fee_monthly is None

    # 5. 相簿與高畫質替換驗證
    assert detail.cover_image_url is not None
    assert "width=1200&height=900" in detail.cover_image_url
    assert len(detail.image_urls) == 17
    for u in detail.image_urls:
        assert "width=1200&height=900" in u or "/1200/900/" in u


def test_yungching_provider_sale_house_integration():
    """驗證 Provider Registry 正式掛載 Yungching 中古屋領域適配器"""
    provider = registry.get_provider("yungching")
    assert provider is not None
    assert isinstance(provider.sale_house, ISaleHouseProvider)
    assert isinstance(provider.sale_house, SourceYungchingSaleHouseProvider)
