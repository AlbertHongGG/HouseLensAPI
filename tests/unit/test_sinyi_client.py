"""HouseLensAPI - 信義房屋非同步 HTTP 客戶端單元測試 (Unit Tests for Sinyi Client)"""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from src.core.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
)
from src.providers.source_sinyi.client import FALLBACK_SEED_SID, SourceSinyiClient
from src.providers.source_sinyi.crypto import SinyiCryptoService


@pytest.mark.asyncio
async def test_ensure_sid_success_from_gateway():
    """測試 ensure_sid 成功自網關取得全新 sid"""
    crypto = SinyiCryptoService()
    client = SourceSinyiClient(crypto=crypto)

    mock_session_payload = {
        "retCode": "000000",
        "retMsg": "成功",
        "content": {"sid": "20261008041801698"},
    }
    encrypted = crypto.encrypt_request_payload(mock_session_payload, wrap_param=False)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = encrypted["data"]

    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.is_closed = False
    mock_http_client.post.return_value = mock_resp

    with patch.object(client, "get_mobile_client", return_value=mock_http_client):
        sid = await client.ensure_sid()
        assert sid == "20261008041801698"
        assert client._cached_sid == "20261008041801698"


@pytest.mark.asyncio
async def test_ensure_sid_fallback_on_network_error():
    """測試 getSession 發生異常時平滑回退至備用種子 sid"""
    client = SourceSinyiClient()
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.is_closed = False
    mock_http_client.post.side_effect = httpx.NetworkError("Session gateway down")

    with patch.object(client, "get_mobile_client", return_value=mock_http_client):
        sid = await client.ensure_sid()
        assert sid == FALLBACK_SEED_SID
        assert client._cached_sid == FALLBACK_SEED_SID


@pytest.mark.asyncio
class TestSourceSinyiClient:
    """SourceSinyiClient 手機端雙向加密網關核心行為測試"""

    async def test_post_mobile_api_success_flow(self):
        """測試手機端加密請求發送與解密接收成功流程 (含 sid 緩存情境)"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)
        client._cached_sid = "test_valid_sid_123"

        # 模擬伺服器回傳有效業務資料
        mock_response_data = {
            "retCode": "000000",
            "retMsg": "成功",
            "content": {"items": [1, 2, 3]},
        }
        # 加密該資料以作為 Mock 回應
        encrypted_resp = crypto.encrypt_request_payload(mock_response_data, wrap_param=False)
        mock_b64_cipher = encrypted_resp["data"]

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = mock_b64_cipher

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_mobile_client", return_value=mock_http_client):
            res = await client.post_mobile_api("/test_endpoint.php", {"my_query": "taipei"})

            assert res["retCode"] == "000000"
            assert res["content"]["items"] == [1, 2, 3]
            # 驗證 HTTP post 被呼叫且包含 sid 標頭
            mock_http_client.post.assert_called_once()
            _, kwargs = mock_http_client.post.call_args
            assert "headers" in kwargs
            assert kwargs["headers"]["sid"] == "test_valid_sid_123"
            assert "json" in kwargs
            assert "param" in kwargs["json"]

    async def test_post_mobile_api_connection_timeout(self):
        """測試連線逾時轉換為 ProviderConnectionError"""
        client = SourceSinyiClient()
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = httpx.ConnectTimeout("Connection timed out")

        with patch.object(client, "get_mobile_client", return_value=mock_http_client):
            with pytest.raises(ProviderConnectionError) as exc_info:
                await client.post_mobile_api("/test.php", {})
            assert "sinyi" in str(exc_info.value)

    async def test_post_mobile_api_rate_limit_429(self):
        """測試 HTTP 429 轉換為 RateLimitExceededError"""
        client = SourceSinyiClient()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_mobile_client", return_value=mock_http_client):
            with pytest.raises(RateLimitExceededError):
                await client.post_mobile_api("/test.php", {})

    async def test_post_mobile_api_business_error_code(self):
        """測試伺服器業務狀態碼非 000000 轉換為 ProviderResponseError"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)

        error_data = {"retCode": "999999", "retMsg": "參數檢核失敗"}
        encrypted_resp = crypto.encrypt_request_payload(error_data, wrap_param=False)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = encrypted_resp["data"]

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.return_value = mock_resp

        with patch.object(client, "get_mobile_client", return_value=mock_http_client):
            with pytest.raises(ProviderResponseError) as exc_info:
                await client.post_mobile_api("/test.php", {})
            assert "999999" in str(exc_info.value)
            assert "參數檢核失敗" in str(exc_info.value)

    async def test_post_mobile_api_retry_on_000991_invalid_sid(self):
        """測試遭遇 000991 sid無效 時自動換發新 sid 並重新請求一次成功"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)
        client._cached_sid = "expired_sid"

        # 第一次回應 000991
        err_data = {"retCode": "000991", "retMsg": "sid無效"}
        err_cipher = crypto.encrypt_request_payload(err_data, wrap_param=False)["data"]
        err_resp = MagicMock(spec=httpx.Response, status_code=200, text=err_cipher)

        # 換發 sid 回應
        session_data = {"retCode": "000000", "content": {"sid": "fresh_new_sid_888"}}
        session_cipher = crypto.encrypt_request_payload(session_data, wrap_param=False)["data"]
        session_resp = MagicMock(spec=httpx.Response, status_code=200, text=session_cipher)

        # 第二次請求業務成功回應
        ok_data = {"retCode": "000000", "retMsg": "成功", "content": {"ok": True}}
        ok_cipher = crypto.encrypt_request_payload(ok_data, wrap_param=False)["data"]
        ok_resp = MagicMock(spec=httpx.Response, status_code=200, text=ok_cipher)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = [err_resp, session_resp, ok_resp]

        with patch.object(client, "get_mobile_client", return_value=mock_http_client):
            result = await client.post_mobile_api("/test.php", {"k": "v"})
            assert result["retCode"] == "000000"
            assert result["content"]["ok"] is True
            assert client._cached_sid == "fresh_new_sid_888"
            assert mock_http_client.post.call_count == 3
