"""HouseLensAPI - 永慶房屋資料模型正規化與相簿 DTO 單元測試套件

使用封包紀錄/yungching 底下真實 API 回應封包進行完整斷言驗證。
"""

import json
from pathlib import Path
import pytest

from src.core.registry import registry
from src.domain.common import GeoPoint
from src.domain.community import NormalizedCommunitySummary
from src.providers.source_yungching.mappers.community_mapper import (
    _parse_facilities,
    map_yungching_community_detail,
    map_yungching_community_summary,
)
from src.providers.source_yungching.mappers.photos_dto import (
    SourceYungchingPhotosDTO,
    normalize_yungching_image_url,
)
import src.providers  # 載入註冊


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "封包紀錄" / "yungching"


def _load_fixture_json(filename: str) -> dict:
    filepath = FIXTURE_DIR / filename
    content = filepath.read_text(encoding="utf-8")
    # 封包檔開頭可能包含 HTTP 標頭，提取第一個 '{' 到結尾
    json_start = content.find("{")
    if json_start != -1:
        content = content[json_start:]
    return json.loads(content)


def test_normalize_yungching_image_url():
    """測試永慶圖片動態尺寸正規化替換"""
    # 1. 佔位符模板替換
    template_url = "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCBUD01/IMG_0022.JPG"
    assert normalize_yungching_image_url(template_url) == (
        "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCBUD01/IMG_0022.JPG"
    )

    # 2. 縮圖路由替換
    thumb_url = "https://pic.yungching.com.tw/res/DrawImage/ShowPic/240/180/YCBUD01/Out/thumb.jpg"
    assert normalize_yungching_image_url(thumb_url) == (
        "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCBUD01/Out/thumb.jpg"
    )

    # 3. 空值處理
    assert normalize_yungching_image_url(None) is None
    assert normalize_yungching_image_url("") is None


def test_source_yungching_photos_dto():
    """測試相簿 DTO 封面置頂、動態尺寸升級與去重保序"""
    raw_payload = {
        "Cover": "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCBUD01/cover.jpg",
        "Pictures": [
            "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCBUD01/pic1.jpg",
            "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCBUD01/cover.jpg",  # 重複封面
            "https://pic.yungching.com.tw/res/DrawImage/ShowPic/{0}/{1}/YCBUD01/pic2.jpg",
        ],
    }
    dto = SourceYungchingPhotosDTO(raw_payload)
    urls = dto.image_urls

    assert len(urls) == 3
    # 封面強制置頂至第一順位
    assert urls[0] == "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCBUD01/cover.jpg"
    assert urls[1] == "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCBUD01/pic1.jpg"
    assert urls[2] == "https://pic.yungching.com.tw/res/DrawImage/ShowPic/1200/900/YCBUD01/pic2.jpg"
    assert dto.cover_url == urls[0]


def test_parse_facilities():
    """測試公設正則萃取與去贅字"""
    raw_text = "千坪基地氣派大樓~公設約28%~公共設備完善(健身房、交誼廳、兒童遊戲室、多功能空間、視聽影音室等..)"
    facilities = _parse_facilities(raw_text)
    assert facilities == ["健身房", "交誼廳", "兒童遊戲室", "多功能空間", "視聽影音室"]


def test_map_yungching_community_summary_real_fixture():
    """使用真實社區清單封包斷言最小必要資訊映射"""
    data = _load_fixture_json("社區清單 Respond.json")
    list_objs = data.get("Data", {}).get("ListObjects", [])
    assert len(list_objs) > 0

    first_item = list_objs[0]  # 42306 台北晶麒
    summary = map_yungching_community_summary(first_item)

    assert summary.provider_id == "yungching"
    assert summary.external_community_id == "42306"
    assert summary.community_name == "台北晶麒"
    assert summary.address == "臺北市萬華區康定路"
    assert summary.coordinates is not None
    assert summary.coordinates.lat == pytest.approx(25.0394756)
    assert summary.coordinates.lng == pytest.approx(121.5020431)
    assert summary.avg_unit_price_wan == pytest.approx(75.8)
    assert "1200/900" in summary.cover_image_url

    # 清單無客觀欄位之屬性為 None
    assert summary.building_type is None
    assert summary.purpose is None
    assert summary.housing_status is None
    assert summary.shopping_district is None
    assert summary.transport is None


def test_map_yungching_community_detail_real_fixture():
    """使用真實社區詳情封包 (全坤威峰) 斷言兩層式 SSOT 屬性映射與為空規範"""
    detail_data = _load_fixture_json("社區詳情資訊 Respond.json")

    # 模擬清單第一層傳遞之最小必要 summary
    real_cover = normalize_yungching_image_url(detail_data["Data"]["Cover"])
    mock_summary = NormalizedCommunitySummary(
        provider_id="yungching",
        external_community_id="43035",
        community_name="全坤威峰",
        region_name="",
        section_name="",
        address="台北市萬華區貴陽街二段",
        coordinates=GeoPoint(lat=25.0397, lng=121.5051),
        avg_unit_price_wan=91.4,
        cover_image_url=real_cover,
    )

    detail = map_yungching_community_detail(summary=mock_summary, raw_detail=detail_data)

    # 1. 最小必要資訊 100% 來自 summary
    assert detail.provider_id == "yungching"
    assert detail.external_community_id == "43035"
    assert detail.community_name == "全坤威峰"
    assert detail.address == "台北市萬華區貴陽街二段"
    assert detail.coordinates.lat == pytest.approx(25.0397)
    assert detail.coordinates.lng == pytest.approx(121.5051)
    assert detail.avg_unit_price_wan == pytest.approx(91.4)
    assert detail.cover_image_url == mock_summary.cover_image_url

    # 2. 剩下的主檔屬性 100% 來自詳情 API
    assert detail.region_name == "台北市"
    assert detail.section_name == "萬華區"
    assert detail.building_age_years == pytest.approx(8.0)
    assert detail.total_households == 382
    assert detail.floor_plan == "地上 19層/地下 1~3層"
    assert detail.structure == "鋼筋混凝土(RC)"
    assert detail.developer_company == "全坤建設"
    assert "健身房" in detail.facilities
    assert detail.url == "https://community.yungching.com.tw/building/43035"
    assert len(detail.image_urls) == 6
    assert all("1200/900" in u for u in detail.image_urls)
    assert detail.image_urls[0] == detail.cover_image_url

    # 3. 客觀未提供欄位 100% 為 None (入庫為 SQL NULL)
    assert detail.building_type is None
    assert detail.purpose is None
    assert detail.housing_status is None
    assert detail.base_area_pin is None
    assert detail.public_ratio_pct is None
    assert detail.parking_count is None
    assert detail.parking_ratio is None
    assert detail.min_parking_price_wan is None
    assert detail.max_parking_price_wan is None
    assert detail.parking_type is None
    assert detail.manage_fee_per_pin is None
    assert detail.shopping_district is None
    assert detail.land_division is None
    assert detail.orientation is None
    assert detail.landscape_designer is None
    assert detail.public_facility_designer is None
    assert detail.builder_company is None


def test_yungching_provider_registry():
    """驗證永慶房屋來源註冊至 ProviderRegistry 與接口相容性"""
    provider = registry.get_provider("yungching")
    assert provider is not None
    assert provider.provider_id == "yungching"
    assert "永慶" in provider.provider_name
    assert provider.community is not None
    assert provider.diagnostics is not None

    # 別名查詢驗證
    assert registry.get_provider("yc") is provider
    assert registry.get_provider("source_yungching") is provider
