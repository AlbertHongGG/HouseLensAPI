"""HouseLensAPI - 信義房屋網頁端 HTTP 客戶端單元測試 (Unit Tests for Sinyi Web Client)"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from src.core.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
)
from src.providers.source_sinyi.client import SinyiWebSession, SourceSinyiClient
from src.providers.source_sinyi.config import (
    DEFAULT_WEB_DEVICE_PAYLOAD,
    FALLBACK_SEED_WEB_SAT,
    FALLBACK_SEED_WEB_SID,
    SINYI_WEB_API_BASE_URL,
    SINYI_WEB_BASE_HEADERS,
)
from src.providers.source_sinyi.crypto import SinyiCryptoService


@pytest.mark.asyncio
class TestSourceSinyiWebClient:
    """測試 SourceSinyiClient 網頁端通訊、動態會話握手與自動修復 (post_web_api)"""

    async def test_get_web_client_headers(self):
        """測試網頁端專屬連線池初始化純淨基礎標頭 (不含動態 sat/sid) 與單例機制"""
        client = SourceSinyiClient()
        try:
            http_client = await client.get_web_client()
            assert http_client.headers.get("code") == "0"
            assert http_client.headers.get("Origin") == "https://www.sinyi.com.tw"
            assert "sat" not in http_client.headers
            assert "sid" not in http_client.headers

            # 再次呼叫應取得同一連線池實例
            http_client_2 = await client.get_web_client()
            assert http_client is http_client_2
        finally:
            await client.close()

    async def test_ensure_web_session_success_handshake(self):
        """測試 ensure_web_session 成功依序執行 appSetup 與 getSession 兩階段握手"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)

        # 模擬 appSetup 回應
        setup_payload = {
            "retCode": "200",
            "retMsg": "執行成功 253",
            "content": {"accessCode": "888123"},
        }
        setup_cipher = crypto.encrypt_request_payload(setup_payload, wrap_param=False)["data"]
        setup_resp = MagicMock(spec=httpx.Response, status_code=200, text=setup_cipher)

        # 模擬 getSession 回應
        session_payload = {
            "retCode": "200",
            "retMsg": "執行成功 253",
            "content": {"sid": "20261008888888888"},
        }
        session_cipher = crypto.encrypt_request_payload(session_payload, wrap_param=False)["data"]
        session_resp = MagicMock(spec=httpx.Response, status_code=200, text=session_cipher)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = [setup_resp, session_resp]

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            session = await client.ensure_web_session()

            assert isinstance(session, SinyiWebSession)
            assert session.sat == "888123"
            assert session.sid == "20261008888888888"
            assert client._cached_web_session == session
            assert mock_http_client.post.call_count == 2

            # 驗證第二次呼叫直接返回快取，不重複發送請求
            cached_session = await client.ensure_web_session()
            assert cached_session is session
            assert mock_http_client.post.call_count == 2

        await client.close()

    async def test_ensure_web_session_fallback_on_error(self):
        """測試兩階段握手遭遇網路或遠端伺服器異常時平滑降級回退至備用種子憑證"""
        client = SourceSinyiClient()
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = httpx.NetworkError("Remote handshake server unavailable")

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            session = await client.ensure_web_session()

            assert session.sat == FALLBACK_SEED_WEB_SAT
            assert session.sid == FALLBACK_SEED_WEB_SID
            assert client._cached_web_session == session

        await client.close()

    async def test_ensure_web_session_concurrency_double_checked_lock(self):
        """測試高併發情況下雙重檢查鎖確保兩階段握手僅執行一次"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)

        setup_payload = {"retCode": "200", "content": {"accessCode": "777001"}}
        setup_cipher = crypto.encrypt_request_payload(setup_payload, wrap_param=False)["data"]
        setup_resp = MagicMock(spec=httpx.Response, status_code=200, text=setup_cipher)

        session_payload = {"retCode": "200", "content": {"sid": "20261008777001"}}
        session_cipher = crypto.encrypt_request_payload(session_payload, wrap_param=False)["data"]
        session_resp = MagicMock(spec=httpx.Response, status_code=200, text=session_cipher)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = [setup_resp, session_resp]

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            # 同時啟動 5 個協程獲取會話
            results = await asyncio.gather(*[client.ensure_web_session() for _ in range(5)])

            for res in results:
                assert res.sat == "777001"
                assert res.sid == "20261008777001"

            # 驗證握手端點只被呼叫了 2 次 (appSetup 1 次 + getSession 1 次)
            assert mock_http_client.post.call_count == 2

        await client.close()

    async def test_post_web_api_success_with_dynamic_headers(self):
        """測試 post_web_api 正常發送純 JSON 並動態注入最新 sat 與 sid 標頭"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)
        client._cached_web_session = SinyiWebSession(sat="my_sat_999", sid="my_sid_999")

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

            mock_http_client.post.assert_called_once()
            call_args, call_kwargs = mock_http_client.post.call_args
            assert call_args[0] == f"{SINYI_WEB_API_BASE_URL}/searchCommunity.php"

            # 驗證動態 sat 與 sid 成功注入於標頭
            headers = call_kwargs["headers"]
            assert headers["sat"] == "my_sat_999"
            assert headers["sid"] == "my_sid_999"

            # 驗證酬載補齊指紋
            posted_json = call_kwargs["json"]
            assert posted_json["filter"] == {"retType": 2}
            assert posted_json["model"] == "web"
            assert posted_json["domain"] == "www.sinyi.com.tw"

            # 驗證回應解密正確
            assert res["retCode"] == "200"
            assert res["content"]["totalCnt"] == 1
            assert res["content"]["object"][0]["commName"] == "帝國花園"

        await client.close()

    async def test_post_web_api_retry_on_308_token_error(self):
        """測試 post_web_api 遭遇 308 認證Token錯誤時自動觸發會話換發重試成功"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)
        client._cached_web_session = SinyiWebSession(sat="old_sat", sid="old_sid")

        # 1. 第一次業務請求返回 308 錯誤
        err_payload = {"retCode": "308", "retMsg": "認證Token錯誤"}
        err_resp = MagicMock(
            spec=httpx.Response,
            status_code=200,
            text=crypto.encrypt_request_payload(err_payload, wrap_param=False)["data"],
        )

        # 2. appSetup 回應
        setup_payload = {"retCode": "200", "content": {"accessCode": "fresh_sat"}}
        setup_resp = MagicMock(
            spec=httpx.Response,
            status_code=200,
            text=crypto.encrypt_request_payload(setup_payload, wrap_param=False)["data"],
        )

        # 3. getSession 回應
        session_payload = {"retCode": "200", "content": {"sid": "fresh_sid"}}
        session_resp = MagicMock(
            spec=httpx.Response,
            status_code=200,
            text=crypto.encrypt_request_payload(session_payload, wrap_param=False)["data"],
        )

        # 4. 第二次業務請求返回成功
        ok_payload = {"retCode": "200", "retMsg": "成功", "content": {"status": "ok"}}
        ok_resp = MagicMock(
            spec=httpx.Response,
            status_code=200,
            text=crypto.encrypt_request_payload(ok_payload, wrap_param=False)["data"],
        )

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        # 依序回傳：第一次業務請求 (308) -> appSetup -> getSession -> 第二次業務請求 (200)
        mock_http_client.post.side_effect = [err_resp, setup_resp, session_resp, ok_resp]

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            res = await client.post_web_api("/searchCommunity.php", {"test": 1})

            assert res["retCode"] == "200"
            assert res["content"]["status"] == "ok"
            assert client._cached_web_session.sat == "fresh_sat"
            assert client._cached_web_session.sid == "fresh_sid"
            assert mock_http_client.post.call_count == 4

        await client.close()

    async def test_post_web_api_business_error(self):
        """測試 post_web_api 遇到不可重試之業務錯誤代碼 (如 500) 轉換為 ProviderResponseError"""
        crypto = SinyiCryptoService()
        client = SourceSinyiClient(crypto=crypto)
        client._cached_web_session = SinyiWebSession(sat="test_sat", sid="test_sid")

        mock_resp_payload = {
            "retCode": "500",
            "retMsg": "伺服器內部錯誤",
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
            assert "500" in str(exc_info.value)
            assert "伺服器內部錯誤" in str(exc_info.value)

        await client.close()

    async def test_post_web_api_http_429_rate_limit(self):
        """測試 post_web_api HTTP 429 觸發 RateLimitExceededError"""
        client = SourceSinyiClient()
        client._cached_web_session = SinyiWebSession(sat="test_sat", sid="test_sid")

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
        client._cached_web_session = SinyiWebSession(sat="test_sat", sid="test_sid")

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.post.side_effect = httpx.NetworkError("DNS resolve failed")

        with patch.object(client, "get_web_client", return_value=mock_http_client):
            with pytest.raises(ProviderConnectionError):
                await client.post_web_api("/searchCommunity.php", {})

        await client.close()
