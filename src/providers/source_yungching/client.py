"""HouseLensAPI - 永慶房屋專屬非同步 HTTP 客戶端 (Source Yungching Client)

封裝永慶房屋 Base URL、必要請求標頭自動注入 (User-Agent, deviceuid, universalid)、
預設 Query 參數注入 (OSType=1, Method=Inquire) 與統一核心異常處理。
"""

import asyncio
import logging
from typing import Any, Dict, Optional
import httpx

from src.core.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)

YUNGCHING_BASE_URL = "https://wapi.yungching.com.tw"
DEFAULT_USER_AGENT = "YCSearchApp_Android"
DEFAULT_DEVICE_UID = "8227c339f9d29135"
DEFAULT_UNIVERSAL_ID = "3a8ccff5-71d8-42f0-babc-72b69904c671"

DEFAULT_QUERY_PARAMS: Dict[str, Any] = {
    "Method": "Inquire",
    "DeviceUid": DEFAULT_DEVICE_UID,
    "OSType": "1",
}


class SourceYungchingClient:
    """永慶房屋平台專屬非同步 HTTP Client"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def get_client(self) -> httpx.AsyncClient:
        """取得或建立 AsyncClient 連線池 (跨事件循環安全)"""
        current_loop = asyncio.get_running_loop()
        if (
            self._client is None
            or self._client.is_closed
            or self._loop != current_loop
            or (self._loop and self._loop.is_closed())
        ):
            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "deviceuid": DEFAULT_DEVICE_UID,
                "universalid": DEFAULT_UNIVERSAL_ID,
                "Accept-Encoding": "gzip",
            }
            self._loop = current_loop
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """發送 GET 請求並解析永慶房屋標準 JSON 回應"""
        url = f"{YUNGCHING_BASE_URL}{path}"
        client = await self.get_client()

        merged_params = dict(DEFAULT_QUERY_PARAMS)
        if params:
            merged_params.update(params)

        try:
            response = await client.get(url, params=merged_params, headers=headers)
        except httpx.ConnectTimeout as e:
            raise ProviderConnectionError("yungching", f"連線至永慶房屋逾時: {url}") from e
        except httpx.NetworkError as e:
            raise ProviderConnectionError("yungching", f"永慶房屋網路連線異常: {e}") from e

        if response.status_code == 429:
            raise RateLimitExceededError("yungching", "觸發永慶房屋請求頻率限制 (HTTP 429)")

        if response.status_code == 403:
            raise RateLimitExceededError("yungching", "永慶房屋存取被拒絕 (HTTP 403)，請確認標頭配置")

        if response.status_code != 200:
            raise ProviderResponseError("yungching", f"永慶房屋 HTTP 狀態碼異常: {response.status_code}")

        try:
            data = response.json()
        except Exception as e:
            raise ProviderResponseError("yungching", f"永慶房屋回應非有效 JSON: {response.text[:200]}") from e

        return data

    async def close(self):
        """關閉連線池"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
