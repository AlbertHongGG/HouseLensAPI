"""HouseLensAPI - 信義房屋中古屋查詢條件建構器單元測試 (Unit Tests for Sale House Query Builder)"""

import pytest

from src.domain.enums import Region
from src.domain.sale_house import SaleHouseSearchQuery
from src.providers.source_sinyi.geo import resolve_sinyi_zipcodes
from src.providers.source_sinyi.query_builders import SinyiSaleHouseQueryBuilder


class TestSinyiSaleHouseQueryBuilder:
    """測試信義房屋中古屋查詢條件建構器"""

    def test_resolve_sinyi_zipcodes_city_level(self):
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI)
        assert len(codes) == 12
        assert "100" in codes
        assert "103" in codes
        assert "116" in codes

    def test_resolve_sinyi_zipcodes_district_level(self):
        codes = resolve_sinyi_zipcodes(region_id=Region.TAIPEI, section_name="大同區")
        assert codes == ["103"]

        codes_fuzzy = resolve_sinyi_zipcodes(region_name="台北市", section_name="大安")
        assert codes_fuzzy == ["106"]

    def test_resolve_sinyi_price_payload(self):
        p1 = SinyiSaleHouseQueryBuilder.resolve_price_payload(min_price_wan=2000, max_price_wan=3000)
        assert p1 == {"priceType": 2, "priceRange": ["2000-3000"]}

        p2 = SinyiSaleHouseQueryBuilder.resolve_price_payload(max_price_wan=1500)
        assert p2 == {"priceType": 2, "priceRange": ["0-1500"]}

        p3 = SinyiSaleHouseQueryBuilder.resolve_price_payload(min_price_wan=5000)
        assert p3 == {"priceType": 2, "priceRange": ["5000-99999"]}

        assert SinyiSaleHouseQueryBuilder.resolve_price_payload() is None

    def test_resolve_sinyi_age_payload(self):
        a1 = SinyiSaleHouseQueryBuilder.resolve_age_payload(max_age_years=5.0)
        assert a1 == ["min-5"]

        a2 = SinyiSaleHouseQueryBuilder.resolve_age_payload(min_age_years=3.0, max_age_years=15.0)
        assert a2 == ["min-5", "5-10", "10-20"]

        assert SinyiSaleHouseQueryBuilder.resolve_age_payload() is None

    def test_build_search_payload_full(self):
        query = SaleHouseSearchQuery(
            page=2,
            page_size=30,
            region_id=Region.TAIPEI,
            keywords="敦品苑",
            min_price_wan=2500,
            max_price_wan=3500,
            max_age_years=10.0,
            sort_order="price_asc",
        )
        payload = SinyiSaleHouseQueryBuilder.build_search_payload(query)
        assert payload["page"] == 2
        assert payload["pageCnt"] == 30
        assert payload["sort"] == "price-asc"
        f = payload["filter"]
        assert f["retType"] == 2
        assert f["keyword"] == {"keyword": "敦品苑"}
        assert f["price"] == {"priceType": 2, "priceRange": ["2500-3500"]}
        assert f["houseAge"] == ["min-5", "5-10"]
        assert len(f["retRange"]) == 12
