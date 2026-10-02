"""Unit Tests for Search Query Introspection and BaseSearchQuery.

驗證各領域搜尋條件規格模型之自省提取與多餘欄位寬容忽略機制 (Decoupled Parameter Ingestion).
"""

from typing import Optional
from pydantic import BaseModel, computed_field
import pytest

from src.domain.common import BaseSearchQuery
from src.domain.community import CommunitySearchQuery
from src.domain.new_house import NewHouseSearchQuery
from src.domain.sale_house import SaleHouseSearchQuery


class DummyUnifiedOptions(BaseModel):
    """模擬全域同步參數物件 (含所有可能之業務維度)"""

    region_id: int = 1
    section_id: Optional[int] = 100
    keywords: Optional[str] = "信義大安"
    min_age_years: Optional[float] = 5.0
    max_age_years: Optional[float] = 10.0
    min_price_wan: Optional[int] = 1500
    max_price_wan: Optional[int] = 3000
    is_presale: bool = True
    is_new_construction: bool = False
    limit: Optional[int] = 50
    extra_unrelated_field: str = "should_be_ignored"

    @computed_field
    @property
    def page_size(self) -> int:
        return 20


def test_base_search_query_extra_ignore():
    """驗證 BaseSearchQuery 自然忽略未定義屬性且不噴錯"""
    raw_data = {
        "region_id": 1,
        "keywords": "捷運站",
        "random_field": 12345,
        "page": 2,
        "page_size": 15,
    }
    query = BaseSearchQuery.model_validate(raw_data)
    assert query.region_id == 1
    assert query.keywords == "捷運站"
    assert query.page == 2
    assert query.page_size == 15
    assert not hasattr(query, "random_field")


def test_community_search_query_from_options():
    """驗證社區模型僅自省吸納屋齡與通用欄位，自然忽略價格與新建案狀態"""
    opts = DummyUnifiedOptions()
    query = CommunitySearchQuery.from_options(opts)

    # 應成功吸納的欄位
    assert query.region_id == 1
    assert query.section_id == 100
    assert query.keywords == "信義大安"
    assert not hasattr(query, "keyword")  # 徹底無相容別名包袱
    assert query.min_age_years == 5.0
    assert query.max_age_years == 10.0
    assert query.page_size == 20

    # 不應存在的欄位 (不在 CommunitySearchQuery schema 內)
    assert not hasattr(query, "min_price_wan")
    assert not hasattr(query, "is_presale")
    assert not hasattr(query, "extra_unrelated_field")


def test_sale_house_search_query_from_options():
    """驗證中古屋模型自省吸納屋齡、總價與通用欄位，自然忽略新建案狀態"""
    opts = DummyUnifiedOptions()
    query = SaleHouseSearchQuery.from_options(opts)

    # 應成功吸納的欄位
    assert query.region_id == 1
    assert query.section_id == 100
    assert query.keywords == "信義大安"
    assert query.min_price_wan == 1500
    assert query.max_price_wan == 3000
    assert query.min_age_years == 5.0
    assert query.max_age_years == 10.0
    assert query.page_size == 20

    # 不應存在的欄位
    assert not hasattr(query, "is_presale")
    assert not hasattr(query, "extra_unrelated_field")


def test_new_house_search_query_from_options():
    """驗證新建案模型自省吸納建案狀態與通用欄位，自然忽略屋齡與價格欄位"""
    opts = DummyUnifiedOptions()
    query = NewHouseSearchQuery.from_options(opts)

    # 應成功吸納的欄位
    assert query.region_id == 1
    assert query.keywords == "信義大安"
    assert query.is_presale is True
    assert query.is_new_construction is False
    assert query.page_size == 20

    # 自然忽略的欄位 (新建案本質無屋齡與二手總價維度)
    assert not hasattr(query, "min_age_years")
    assert not hasattr(query, "max_age_years")
    assert not hasattr(query, "min_price_wan")
    assert not hasattr(query, "extra_unrelated_field")


def test_from_options_with_dict():
    """驗證直接傳入字典時亦能正確自省轉換"""
    data = {
        "region_id": 2,
        "keywords": "七期",
        "min_age_years": 1.0,
        "max_age_years": 8.0,
        "arbitrary_flag": True,
    }
    comm_query = CommunitySearchQuery.from_options(data)
    assert comm_query.region_id == 2
    assert comm_query.keywords == "七期"
    assert comm_query.min_age_years == 1.0
    assert comm_query.max_age_years == 8.0

    nh_query = NewHouseSearchQuery.from_options(data)
    assert nh_query.region_id == 2
    assert nh_query.keywords == "七期"
    assert not hasattr(nh_query, "min_age_years")


def test_application_package_exports():
    """驗證 src.application 模組之 __all__ 導出完備且無未定義符號"""
    import src.application as app_pkg

    for name in app_pkg.__all__:
        assert hasattr(app_pkg, name), f"Missing exported symbol: {name}"

    assert hasattr(app_pkg, "SyncOptions")
    assert hasattr(app_pkg, "InspectUseCase")
    assert hasattr(app_pkg, "SyncUseCase")
