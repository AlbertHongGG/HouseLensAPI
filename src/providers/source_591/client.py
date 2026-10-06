"""HouseLensAPI - 591 專屬非同步 HTTP 客戶端 (Source 591 Client)

封裝網域自動路由、標頭自動注入 (User-Agent, device, deviceid) 與統一錯誤處理。
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

DEFAULT_APP_UA = (
    "com.addcn.android.house591/8.13.0.975/1080x2274/Android/10/SM-A315G/675ad1fc-ebc4-4310-8df7-7e8dd5b0c051"
)
DEFAULT_DEVICE_ID = "675ad1fc-ebc4-4310-8df7-7e8dd5b0c051"

DEFAULT_591_QUERY_PARAMS: Dict[str, Any] = {
    "mobile_id": DEFAULT_DEVICE_ID,
    "deviceid": DEFAULT_DEVICE_ID,
    "device_id": DEFAULT_DEVICE_ID,
    "version": "8.13.0.975",
    "device": "android",
}

# 依實測驗證之官方 Canonical Domains
CANONICAL_DOMAINS = {
    "house": "https://bff-house.591.com.tw",
    "market": "https://bff-market.591.com.tw",
    "newhouse": "https://bff-newhouse.591.com.tw",
}


class Source591Client:
    """591 平台專屬 HTTP Client"""

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
                "User-Agent": DEFAULT_APP_UA,
                "Accept": "application/json, text/plain, */*",
                "device": "android",
                "deviceid": DEFAULT_DEVICE_ID,
                "mobile_id": DEFAULT_DEVICE_ID,
                "version": "8.13.0.975",
                "loginvalid": "0",
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
        domain_type: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """發送 GET 請求並解析 591 標準 JSON 回應"""
        base_url = CANONICAL_DOMAINS.get(domain_type)
        if not base_url:
            raise ValueError(f"未知的網域類型: '{domain_type}'，支援: {list(CANONICAL_DOMAINS.keys())}")

        url = f"{base_url}{path}"
        client = await self.get_client()

        merged_params = dict(DEFAULT_591_QUERY_PARAMS)
        if params:
            merged_params.update(params)

        try:
            response = await client.get(url, params=merged_params, headers=headers)
        except httpx.ConnectTimeout as e:
            raise ProviderConnectionError("591", f"連線至 591 逾時: {url}") from e
        except httpx.NetworkError as e:
            raise ProviderConnectionError("591", f"網路連線異常: {e}") from e

        if response.status_code == 429:
            raise RateLimitExceededError("591", "觸發 591 請求頻率限制 (HTTP 429)")

        if response.status_code == 403:
            raise RateLimitExceededError("591", "存取被拒絕 (HTTP 403)，請確認標頭配置")

        if response.status_code != 200:
            raise ProviderResponseError("591", f"HTTP 狀態碼異常: {response.status_code}")

        try:
            data = response.json()
        except Exception as e:
            raise ProviderResponseError("591", f"回應非有效 JSON: {response.text[:200]}") from e

        # 591 回應結構通常帶有 status: 1 代表成功
        status = data.get("status")
        if status != 1:
            msg = data.get("msg") or data.get("message") or f"status: {status}"
            raise ProviderResponseError("591", f"591 API 回傳業務失敗: {msg}", details=data)

        return data

    async def fetch_sale_community_entry(self, sale_id: str) -> Dict[str, Any]:
        """取得中古屋詳情頁社區入口資訊卡片 (微服務端點)

        端點: GET https://bff-house.591.com.tw/v1/sale/detail/community/entry?id={sale_id}
        """
        clean_id = sale_id.lstrip("S") if sale_id.startswith("S") else sale_id
        params = {"id": clean_id}
        return await self.get("house", "/v1/sale/detail/community/entry", params=params)

    async def fetch_sale_house_photos(self, sale_id: str) -> Dict[str, Any]:
        """取得中古屋房屋相簿圖片列表 (微服務端點)

        端點: GET https://bff-house.591.com.tw/v1/ware/photos?id={sale_id}&type=2
        """
        clean_id = sale_id.lstrip("S") if sale_id.startswith("S") else sale_id
        params = {"id": clean_id, "type": "2"}
        return await self.get("house", "/v1/ware/photos", params=params)

    async def close(self):
        """關閉連線池"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
