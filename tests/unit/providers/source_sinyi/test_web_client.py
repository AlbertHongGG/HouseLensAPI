"""HouseLensAPI - 信義房屋網頁端 HTTP 客戶端單元測試 (Unit Tests for Sinyi Web Client)"""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from src.core.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
)
from src.providers.source_sinyi.client import SourceSinyiClient
from src.providers.source_sinyi.config import (
    DEFAULT_WEB_DEVICE_PAYLOAD,
    SINYI_WEB_API_BASE_URL,
    SINYI_WEB_HEADERS,
)
from src.providers.source_sinyi.crypto import SinyiCryptoService


@pytest.mark.asyncio
class TestSourceSinyiWebClient:
    """測試 SourceSinyiClient 網頁端通訊 (post_web_api)"""

    async def test_get_web_client_headers(self):
        """測試網頁端專屬連線池初始化標頭與單例機制"""
        client = SourceSinyiClient()
        try:
            http_client = await client.get_web_client()
            assert http_client.headers.get("code") == "0"
            assert http_client.headers.get("sat") == "730282"
            assert http_client.headers.get("Origin") == "https://www.sinyi.com.tw"

            # 再次呼叫應取得同一連線池實例
            http_client_2 = await client.get_web_client()
            assert http_client is http_client_2
        finally:
            await client.close()

    async def test_post_web_api_success(self):
        """測試 post_web_api 正常發送純 JSON 且成功解密回應"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)

        mock_resp_payload = {
            "retCode": "200",
            "retMsg": "執行成功 253",
            "content": {
                "totalCnt": 1,
                "object": [{"commId": "G0000316", "commName": "帝國花園"}],
            },
        }
        encrypted = crypto.encrypt_request_payload(mock_resp_payload, wrap_param=False)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = encrypted["data"]

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            res = await client.post_web_api("/searchCommunity.php", {"filter": {"retType": 2}})

            # 驗證傳送 URL 與酬載中自動補齊了網頁裝置指紋
            mock_http_client.post.assert_called_once()
            call_args, call_kwargs = mock_http_client.post.call_args
            assert call_args[0] == f"{SINYI_WEB_API_BASE_URL}/searchCommunity.php"
            posted_json = call_kwargs["json"]
            assert posted_json["filter"] == {"retType": 2}
            assert posted_json["model"] == "web"
            assert posted_json["domain"] == "www.sinyi.com.tw"

            # 驗證業務回應成功解密
            assert res["retCode"] == "200"
            assert res["content"]["totalCnt"] == 1
            assert res["content"]["object"][0]["commName"] == "帝國花園"

        await client.close()

    async def test_post_web_api_business_error(self):
        """測試 post_web_api 遇到業務錯誤代碼 (如 308 認證Token錯誤) 轉換為 ProviderResponseError"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)

        mock_resp_payload = {
            "retCode": "308",
            "retMsg": "認證Token錯誤",
            "content": None,
        }
        encrypted = crypto.encrypt_request_payload(mock_resp_payload, wrap_param=False)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = encrypted["data"]

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            with pytest.raises(ProviderResponseError) as exc_info:
                await client.post_web_api("/searchCommunity.php", {})
            assert "308" in str(exc_info.value)
            assert "認證Token錯誤" in str(exc_info.value)

        await client.close()

    async def test_post_web_api_http_429_rate_limit(self):
        """測試 post_web_api HTTP 429 觸發 RateLimitExceededError"""
        client = SourceSinyiClient()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            with pytest.raises(RateLimitExceededError):
                await client.post_web_api("/searchCommunity.php", {})

        await client.close()

    async def test_post_web_api_network_error(self):
        """測試 post_web_api 網路斷線觸發 ProviderConnectionError"""
        client = SourceSinyiClient()
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = httpx.NetworkError("DNS resolve failed")

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            with pytest.raises(ProviderConnectionError):
                await client.post_web_api("/searchCommunity.php", {})

        await client.close()
