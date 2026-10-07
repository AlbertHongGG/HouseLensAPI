"""HouseLensAPI - 永慶房屋頂層資料來源提供者 (Yungching Source Provider)

整合永慶房屋社區、中古屋領域服務與自主探針，並於模組載入時自動註冊至 ProviderRegistry。
"""

import logging
from typing import Optional

from src.core.interfaces.community import ICommunityProvider
from src.core.interfaces.diagnostics import IProviderDiagnostics
from src.core.interfaces.new_house import INewHouseProvider
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.interfaces.sale_house import ISaleHouseProvider
from src.core.registry import registry
from src.providers.source_yungching.client import SourceYungchingClient
from src.providers.source_yungching.community import SourceYungchingCommunityProvider
from src.providers.source_yungching.diagnostics import SourceYungchingDiagnostics
from src.providers.source_yungching.sale_house import SourceYungchingSaleHouseProvider

logger = logging.getLogger(__name__)


class SourceYungchingProvider(IHouseSourceProvider):
    """永慶房屋平台完整來源外掛模組"""

    def __init__(self, client: Optional[SourceYungchingClient] = None):
        self._client = client or SourceYungchingClient()
        self._community = SourceYungchingCommunityProvider(self._client)
        self._sale_house = SourceYungchingSaleHouseProvider(self._client)
        self._diagnostics = SourceYungchingDiagnostics()

    @property
    def provider_id(self) -> str:
        return "yungching"

    @property
    def provider_name(self) -> str:
        return "永慶房產集團 永慶房仲網"

    @property
    def community(self) -> ICommunityProvider:
        return self._community

    @property
    def sale_house(self) -> ISaleHouseProvider:
        return self._sale_house

    @property
    def new_house(self) -> INewHouseProvider:
        raise NotImplementedError("永慶房屋提供者尚未實作新建案領域服務")

    @property
    def diagnostics(self) -> IProviderDiagnostics:
        return self._diagnostics

    async def health_check(self) -> bool:
        """發送極輕量請求檢查永慶房屋 API 通道健康度"""
        try:
            res = await self._client.get(
                "/v1/SearchCommunityList",
                params={"Page": 1, "Limit": 1, "County": "台北市"},
            )
            return "Data" in res
        except Exception as e:
            logger.warning("永慶房屋健康檢查失敗: %s", e)
            return False

    async def close(self):
        """釋放連線池資源"""
        await self._client.close()


# 自動註冊至全域 Registry
registry.register("yungching", SourceYungchingProvider, aliases=["source_yungching", "yc"])
