"""HouseLensAPI - 信義房屋頂層資料來源提供者 (Sinyi Source Provider)

整合信義房屋非同步 HTTP 客戶端、加密防腐層與自主診斷探針，並於模組載入時自動註冊至 ProviderRegistry。
"""

import logging
from typing import Optional

from src.core.interfaces.community import ICommunityProvider
from src.core.interfaces.diagnostics import IProviderDiagnostics
from src.core.interfaces.new_house import INewHouseProvider
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.interfaces.sale_house import ISaleHouseProvider
from src.core.registry import registry
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.diagnostics import SourceSinyiDiagnostics
from src.providers.source_sinyi.sale_house import SourceSinyiSaleHouseProvider

logger = logging.getLogger(__name__)


class SourceSinyiProvider(IHouseSourceProvider):
    """信義房屋平台完整來源外掛模組"""

    def __init__(self, client: Optional[SourceSinyiClient] = None):
        self._client = client or SourceSinyiClient()
        self._diagnostics = SourceSinyiDiagnostics()
        self._sale_house = SourceSinyiSaleHouseProvider(self._client)

    @property
    def provider_id(self) -> str:
        return "sinyi"

    @property
    def provider_name(self) -> str:
        return "信義房屋 Sinyi Housing"

    @property
    def community(self) -> ICommunityProvider:
        raise NotImplementedError("信義房屋提供者尚未實作社區領域服務")

    @property
    def sale_house(self) -> ISaleHouseProvider:
        return self._sale_house

    @property
    def new_house(self) -> INewHouseProvider:
        raise NotImplementedError("信義房屋提供者尚未實作新建案領域服務")

    @property
    def diagnostics(self) -> IProviderDiagnostics:
        return self._diagnostics

    async def health_check(self) -> bool:
        """發送極輕量加密請求檢查信義房屋 API 通道與加解密機制健康度"""
        try:
            ping_payload = {
                "page": 1,
                "pageCnt": 1,
                "sort": "default",
                "filter": {
                    "retRange": ["100"],
                    "retType": 2,
                },
            }
            res = await self._client.post_encrypted("/filterObject.php", ping_payload)
            return res.get("retCode") == "000000"
        except Exception as e:
            logger.warning("信義房屋健康檢查失敗: %s", e)
            return False

    async def close(self):
        """釋放連線池資源"""
        await self._client.close()


# 自動註冊至全域 Registry
registry.register("sinyi", SourceSinyiProvider, aliases=["source_sinyi", "sy"])
