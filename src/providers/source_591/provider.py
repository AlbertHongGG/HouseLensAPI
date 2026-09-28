"""HouseLensAPI - 591 頂層資料來源提供者 (591 Source Provider)

整合 591 社區、中古屋、新建案三大領域服務，並於模組載入時自動註冊至 ProviderRegistry。
"""

import logging
from typing import Optional

from src.core.interfaces.community import ICommunityProvider
from src.core.interfaces.new_house import INewHouseProvider
from src.core.interfaces.provider import IHouseSourceProvider
from src.core.interfaces.sale_house import ISaleHouseProvider
from src.core.registry import registry
from src.providers.source_591.client import Source591Client
from src.providers.source_591.community import Source591CommunityProvider
from src.providers.source_591.new_house import Source591NewHouseProvider
from src.providers.source_591.sale_house import Source591SaleHouseProvider

logger = logging.getLogger(__name__)


class Source591Provider(IHouseSourceProvider):
    """591 房屋交易平台完整來源外掛模組"""

    def __init__(self, client: Optional[Source591Client] = None):
        self._client = client or Source591Client()
        self._community = Source591CommunityProvider(self._client)
        self._sale_house = Source591SaleHouseProvider(self._client)
        self._new_house = Source591NewHouseProvider(self._client)

    @property
    def provider_id(self) -> str:
        return "591"

    @property
    def provider_name(self) -> str:
        return "數字科技 591 房屋交易"

    @property
    def community(self) -> ICommunityProvider:
        return self._community

    @property
    def sale_house(self) -> ISaleHouseProvider:
        return self._sale_house

    @property
    def new_house(self) -> INewHouseProvider:
        return self._new_house

    async def health_check(self) -> bool:
        """發送極輕量請求檢查 591 API 通道健康度"""
        try:
            res = await self._client.get(
                "market",
                "/v1/search/list",
                params={"page": 1, "page_size": 1, "regionid": 1},
            )
            return res.get("status") == 1
        except Exception as e:
            logger.warning("591 健康檢查失敗: %s", e)
            return False

    async def close(self):
        """釋放連線池資源"""
        await self._client.close()


# 自動註冊至全域 Registry
registry.register("591", Source591Provider, aliases=["source_591"])
