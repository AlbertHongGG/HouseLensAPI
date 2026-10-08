"""HouseLensAPI - 信義房屋頂層提供者單元測試 (Unit Tests for Sinyi Provider)"""

from unittest.mock import AsyncMock
import pytest

from src.core.interfaces.provider import IHouseSourceProvider
from src.core.registry import registry
from src.providers.source_sinyi import SourceSinyiClient, SourceSinyiProvider


def test_registry_contains_sinyi():
    """測試全域 Registry 正確註冊 sinyi 及其別名"""
    assert registry.resolve_id("sinyi") == "sinyi"
    assert registry.resolve_id("source_sinyi") == "sinyi"
    assert registry.resolve_id("sy") == "sinyi"

    instance = registry.get_provider("sinyi")
    assert isinstance(instance, SourceSinyiProvider)
    assert isinstance(instance, IHouseSourceProvider)


def test_sinyi_provider_properties():
    """測試信義提供者基本屬性與未實作領域服務異常"""
    provider = SourceSinyiProvider()
    assert provider.provider_id == "sinyi"
    assert "信義房屋" in provider.provider_name

    from src.core.interfaces.community import ICommunityProvider
    assert isinstance(provider.community, ICommunityProvider)

    from src.core.interfaces.sale_house import ISaleHouseProvider
    assert isinstance(provider.sale_house, ISaleHouseProvider)

    with pytest.raises(NotImplementedError):
        _ = provider.new_house


    assert provider.diagnostics is not None
    assert provider.diagnostics.get_probe("health_ping") is not None
    assert provider.diagnostics.get_probe("sale_list") is not None
    assert provider.diagnostics.get_probe("sale_detail") is not None
    assert provider.diagnostics.get_probe("community_list") is not None
    assert provider.diagnostics.get_probe("community_detail") is not None


@pytest.mark.asyncio
async def test_sinyi_provider_health_check_success():
    """測試 health_check 成功情境"""
    mock_client = AsyncMock(spec=SourceSinyiClient)
    mock_client.post_mobile_api.return_value = {"retCode": "000000", "retMsg": "成功"}

    provider = SourceSinyiProvider(client=mock_client)
    is_healthy = await provider.health_check()
    assert is_healthy is True
    mock_client.post_mobile_api.assert_called_once()


@pytest.mark.asyncio
async def test_sinyi_provider_health_check_failure():
    """測試 health_check 異常回退回傳 False"""
    mock_client = AsyncMock(spec=SourceSinyiClient)
    mock_client.post_mobile_api.side_effect = Exception("Network down")

    provider = SourceSinyiProvider(client=mock_client)
    is_healthy = await provider.health_check()
    assert is_healthy is False
