"""Unit Tests for Core Interfaces and ProviderRegistry"""

import pytest
from typing import List

from src.core.exceptions import ProviderError, ProviderNotFoundError
from src.core.interfaces import (
    ICommunityProvider,
    IHouseSourceProvider,
    INewHouseProvider,
    ISaleHouseProvider,
)
from src.core.registry import ProviderRegistry
from src.domain.common import PageResult
from src.domain.community import CommunityDetail, CommunitySearchQuery, CommunitySummary
from src.domain.new_house import NewHouseDetail, NewHouseSearchQuery, NewHouseSummary
from src.domain.sale_house import SaleHouseDetail, SaleHouseSearchQuery, SaleHouseSummary


class MockCommunityProvider(ICommunityProvider):
    async def search_communities(self, query: CommunitySearchQuery) -> PageResult[CommunitySummary]:
        return PageResult.create(items=[], total_records=0, page=1, page_size=20)

    async def get_community_detail(self, community_id: str) -> CommunityDetail:
        return CommunityDetail(
            community_id=community_id,
            community_name="測試社區",
            address="測試地址",
            region_name="台北市",
            section_name="中正區",
        )


class MockSaleHouseProvider(ISaleHouseProvider):
    async def search_sale_houses(self, query: SaleHouseSearchQuery) -> PageResult[SaleHouseSummary]:
        return PageResult.create(items=[], total_records=0, page=1, page_size=20)

    async def get_sale_house_detail(self, house_id: str) -> SaleHouseDetail:
        return SaleHouseDetail(
            house_id=house_id,
            title="測試房屋",
            price=2000,
        )


class MockNewHouseProvider(INewHouseProvider):
    async def search_new_houses(self, query: NewHouseSearchQuery) -> PageResult[NewHouseSummary]:
        return PageResult.create(items=[], total_records=0, page=1, page_size=20)

    async def get_new_house_detail(self, new_house_id: str) -> NewHouseDetail:
        return NewHouseDetail(
            hid=int(new_house_id),
            project_name="測試建案",
            build_type="預售屋",
            region="台北市",
            section="中正區",
            address="測試路",
        )


class MockSourceProvider(IHouseSourceProvider):
    @property
    def provider_id(self) -> str:
        return "mock_src"

    @property
    def provider_name(self) -> str:
        return "Mock Source Provider"

    @property
    def community(self) -> ICommunityProvider:
        return MockCommunityProvider()

    @property
    def sale_house(self) -> ISaleHouseProvider:
        return MockSaleHouseProvider()

    @property
    def new_house(self) -> INewHouseProvider:
        return MockNewHouseProvider()

    async def health_check(self) -> bool:
        return True


class TestProviderRegistry:
    def test_registry_registration_and_retrieval(self):
        reg = ProviderRegistry()
        reg.register("mock_src", MockSourceProvider, aliases=["mock", "test_src"])

        assert "mock_src" in reg.list_providers()
        assert reg.resolve_id("mock") == "mock_src"
        assert reg.resolve_id("test_src") == "mock_src"

        # Instantiate provider
        provider = reg.get_provider("mock")
        assert isinstance(provider, IHouseSourceProvider)
        assert provider.provider_id == "mock_src"
        assert provider.provider_name == "Mock Source Provider"
        assert isinstance(provider.community, ICommunityProvider)
        assert isinstance(provider.sale_house, ISaleHouseProvider)
        assert isinstance(provider.new_house, INewHouseProvider)

    def test_duplicate_registration_raises_error(self):
        reg = ProviderRegistry()
        reg.register("mock_src", MockSourceProvider)
        with pytest.raises(ProviderError):
            reg.register("mock_src", MockSourceProvider)

    def test_alias_collision_raises_error(self):
        reg = ProviderRegistry()
        reg.register("mock_src", MockSourceProvider, aliases=["m"])
        with pytest.raises(ProviderError):
            reg.register("other_src", MockSourceProvider, aliases=["m"])

    def test_unregistered_provider_raises_not_found(self):
        reg = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            reg.get_provider("non_existent")

    def test_unregister(self):
        reg = ProviderRegistry()
        reg.register("mock_src", MockSourceProvider, aliases=["m"])
        assert "mock_src" in reg.list_providers()
        reg.unregister("mock_src")
        assert "mock_src" not in reg.list_providers()
        with pytest.raises(ProviderNotFoundError):
            reg.resolve_id("m")


@pytest.mark.asyncio
async def test_mock_provider_flow():
    provider = MockSourceProvider()
    assert await provider.health_check() is True

    community_detail = await provider.community.get_community_detail("1001")
    assert community_detail.community_id == "1001"

    house_detail = await provider.sale_house.get_sale_house_detail("S12345")
    assert house_detail.house_id == "S12345"
    assert house_detail.price == 2000

    new_house_detail = await provider.new_house.get_new_house_detail("9999")
    assert new_house_detail.hid == 9999
