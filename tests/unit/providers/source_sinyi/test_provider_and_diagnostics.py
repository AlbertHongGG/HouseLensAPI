"""HouseLensAPI - 信義房屋頂層 Provider 與診斷探針單元測試 (Unit Tests)"""

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from src.core.registry import registry
from src.domain.diagnostics import DiagnosticDomain, DiagnosticStatus
from src.providers.source_sinyi.community import SourceSinyiCommunityProvider
from src.providers.source_sinyi.diagnostics import (
    SinyiCommunityDetailProbe,
    SinyiCommunityListProbe,
    SinyiHealthPingProbe,
    SinyiSaleDetailProbe,
    SinyiSaleListProbe,
    SourceSinyiDiagnostics,
)
from src.providers.source_sinyi.provider import SourceSinyiProvider
from src.providers.source_sinyi.sale_house import SourceSinyiSaleHouseProvider


def test_sinyi_provider_registration_and_properties():
    # 測試全域 Registry 取得實例
    provider = registry.get("sinyi")
    assert isinstance(provider, SourceSinyiProvider)
    assert provider.provider_id == "sinyi"
    assert provider.provider_name == "信義房屋 Sinyi Housing"

    # 驗證中古屋與社區領域介面已成功掛載
    assert isinstance(provider.sale_house, SourceSinyiSaleHouseProvider)
    assert isinstance(provider.community, SourceSinyiCommunityProvider)

    # 驗證診斷套件
    assert isinstance(provider.diagnostics, SourceSinyiDiagnostics)
    probes = provider.diagnostics.get_probes()
    assert len(probes) == 5
    probe_ids = {p.endpoint_id for p in probes}
    assert probe_ids == {
        "health_ping",
        "sale_list",
        "sale_detail",
        "community_list",
        "community_detail",
    }


@pytest.mark.asyncio
async def test_sinyi_diagnostics_probes_execution():
    # 建立 mock httpx client 與 response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"retCode": "000000"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.headers = {"user-agent": "TestClient/1.0"}
    mock_client.request.return_value = mock_response

    # 1. 測試 HealthPingProbe
    ping_probe = SinyiHealthPingProbe()
    assert ping_probe.domain == DiagnosticDomain.SYSTEM
    art_ping = await ping_probe.execute(client=mock_client)
    assert art_ping.metadata.status == DiagnosticStatus.SUCCESS
    assert art_ping.metadata.status_code == 200

    # 2. 測試 SaleListProbe
    list_probe = SinyiSaleListProbe()
    assert list_probe.domain == DiagnosticDomain.SALE
    art_list = await list_probe.execute(client=mock_client)
    assert art_list.metadata.status == DiagnosticStatus.SUCCESS
    assert art_list.metadata.status_code == 200

    # 3. 測試 SaleDetailProbe
    detail_probe = SinyiSaleDetailProbe()
    assert detail_probe.domain == DiagnosticDomain.SALE
    art_detail = await detail_probe.execute(client=mock_client)
    assert art_detail.metadata.status == DiagnosticStatus.SUCCESS
    assert art_detail.metadata.status_code == 200

    # 4. 測試 CommunityListProbe
    comm_list_probe = SinyiCommunityListProbe()
    assert comm_list_probe.domain == DiagnosticDomain.COMMUNITY
    art_comm_list = await comm_list_probe.execute(client=mock_client)
    assert art_comm_list.metadata.status == DiagnosticStatus.SUCCESS
    assert art_comm_list.metadata.status_code == 200

    # 5. 測試 CommunityDetailProbe
    comm_detail_probe = SinyiCommunityDetailProbe()
    assert comm_detail_probe.domain == DiagnosticDomain.COMMUNITY
    art_comm_detail = await comm_detail_probe.execute(client=mock_client)
    assert art_comm_detail.metadata.status == DiagnosticStatus.SUCCESS
    assert art_comm_detail.metadata.status_code == 200
