"""HouseLensAPI - 信義房屋專屬非同步 HTTP 客戶端 (Source Sinyi Client)

封裝信義房屋雙通道 (手機端與網頁端) 網關、getSession 伺服器 Session 自動取得與換發、
雙向 AES-256-ECB 加解密與核心異常轉換。
提供專責公開方法：
- post_mobile_api: 手機端雙向加密網關 (https://sinyiapi.sinyi.com.tw)
- post_web_api: 網頁端專屬網關 (https://sinyiwebapi.sinyi.com.tw)
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Optional
import httpx

from src.core.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
)
from src.providers.source_sinyi.config import (
    DEFAULT_DEVICE_PAYLOAD,
    DEFAULT_WEB_DEVICE_PAYLOAD,
    FALLBACK_SEED_MOBILE_SID,
    FALLBACK_SEED_WEB_SAT,
    FALLBACK_SEED_WEB_SID,
    SINYI_API_BASE_URL,
    SINYI_HEADER_CODE,
    SINYI_USER_AGENT,
    SINYI_WEB_API_BASE_URL,
    SINYI_WEB_BASE_HEADERS,
)
from src.providers.source_sinyi.crypto import SinyiCryptoService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SinyiWebSession:
    """信義房屋網頁端動態會話憑證模型"""

    sat: str  # 初始應用登記碼 (appSetup 取得之 accessCode)
    sid: str  # 會話序號 (getSession 取得之 sid)


class SourceSinyiClient:
    """信義房屋雙通道 (手機端與網頁端) 非同步 HTTP Client"""

    def __init__(
        self,
        base_url: str = SINYI_API_BASE_URL,
        web_base_url: str = SINYI_WEB_API_BASE_URL,
        timeout: float = 15.0,
        crypto: Optional[SinyiCryptoService] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.web_base_url = web_base_url.rstrip("/")
        self.timeout = timeout
        self.crypto = crypto or SinyiCryptoService()
        self._mobile_client: Optional[httpx.AsyncClient] = None
        self._mobile_loop: Optional[asyncio.AbstractEventLoop] = None
        self._web_client: Optional[httpx.AsyncClient] = None
        self._web_loop: Optional[asyncio.AbstractEventLoop] = None
        self._cached_mobile_sid: Optional[str] = None
        self._mobile_sid_lock = asyncio.Lock()
        self._cached_web_session: Optional[SinyiWebSession] = None
        self._web_session_lock = asyncio.Lock()

    async def get_mobile_client(self) -> httpx.AsyncClient:
        """取得或建立手機端專屬 AsyncClient 連線池 (跨事件循環安全防護)"""
        current_loop = asyncio.get_running_loop()
        if (
            self._mobile_client is None
            or self._mobile_client.is_closed
            or self._mobile_loop != current_loop
            or (self._mobile_loop and self._mobile_loop.is_closed())
        ):
            default_headers = {
                "user-agent": SINYI_USER_AGENT,
                "code": SINYI_HEADER_CODE,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "*/*",
                "Accept-Encoding": "gzip",
                "Connection": "Keep-Alive",
            }
            self._mobile_loop = current_loop
            self._mobile_client = httpx.AsyncClient(
                headers=default_headers,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._mobile_client

    async def get_web_client(self) -> httpx.AsyncClient:
        """取得或建立網頁端專屬 AsyncClient 連線池 (跨事件循環安全防護)"""
        current_loop = asyncio.get_running_loop()
        if (
            self._web_client is None
            or self._web_client.is_closed
            or self._web_loop != current_loop
            or (self._web_loop and self._web_loop.is_closed())
        ):
            self._web_loop = current_loop
            self._web_client = httpx.AsyncClient(
                headers=dict(SINYI_WEB_BASE_HEADERS),
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._web_client

    async def ensure_mobile_sid(self, force_refresh: bool = False) -> str:
        """取得或向信義網關換發合法有效的 App 手機端 Session ID (sid)

        信義手機端 API 於資料端點驗證時，要求 sid 必須為經由 /getSession.php 登記之伺服器 Session。
        """
        async with self._mobile_sid_lock:
            if self._cached_mobile_sid and not force_refresh:
                return self._cached_mobile_sid

            try:
                client = await self.get_mobile_client()
                url = f"{self.base_url}/getSession.php"
                resp = await client.post(url)
                if resp.status_code == 200 and resp.text:
                    decrypted = self.crypto.decrypt_response_payload(resp.text)
                    new_sid = decrypted.get("content", {}).get("sid")
                    if new_sid:
                        self._cached_mobile_sid = str(new_sid)
                        logger.debug("成功自信義伺服器取得全新手機端連線 sid: %s", self._cached_mobile_sid)
                        return self._cached_mobile_sid
            except Exception as e:
                logger.warning("向信義網關請求手機端 getSession 失敗，回退至備用種子 sid: %s", e)

            # 若伺服器取得失敗，回退至已驗證之種子 sid
            self._cached_mobile_sid = FALLBACK_SEED_MOBILE_SID
            return self._cached_mobile_sid

    async def _perform_web_handshake(self, client: httpx.AsyncClient) -> SinyiWebSession:
        """執行信義網頁端兩階段動態會話握手協議 (appSetup -> getSession)

        Raises:
            ProviderResponseError: 當握手端點回應錯誤或無法解析出 accessCode/sid。
        """
        # 傳遞完整設備指紋 (包含 19 個必要欄位)，防範信義伺服器檢核參數個數錯誤
        handshake_device_payload = dict(DEFAULT_WEB_DEVICE_PAYLOAD)

        # 第一階段：appSetup.php 取得 accessCode (即日後通訊標頭 sat)
        setup_url = f"{self.web_base_url}/appSetup.php"
        setup_headers = {"sat": "", "sid": ""}
        setup_resp = await client.post(
            setup_url,
            json=handshake_device_payload,
            headers=setup_headers,
        )
        if setup_resp.status_code != 200 or not setup_resp.text:
            raise ProviderResponseError("sinyi", f"網頁端 appSetup 握手失敗 (HTTP {setup_resp.status_code})")

        decrypted_setup = self.crypto.decrypt_response_payload(setup_resp.text)
        access_code = decrypted_setup.get("content", {}).get("accessCode")
        if not access_code:
            ret_msg = decrypted_setup.get("retMsg", "未返回 accessCode")
            raise ProviderResponseError("sinyi", f"網頁端 appSetup 業務異常: {ret_msg}")

        sat_str = str(access_code)

        # 第二階段：getSession.php 攜帶 sat 取得 sid
        session_url = f"{self.web_base_url}/getSession.php"
        session_headers = {"sat": sat_str, "sid": ""}
        session_resp = await client.post(
            session_url,
            json=handshake_device_payload,
            headers=session_headers,
        )
        if session_resp.status_code != 200 or not session_resp.text:
            raise ProviderResponseError("sinyi", f"網頁端 getSession 握手失敗 (HTTP {session_resp.status_code})")

        decrypted_session = self.crypto.decrypt_response_payload(session_resp.text)
        sid_val = decrypted_session.get("content", {}).get("sid")
        if not sid_val:
            ret_msg = decrypted_session.get("retMsg", "未返回 sid")
            raise ProviderResponseError("sinyi", f"網頁端 getSession 業務異常: {ret_msg}")

        sid_str = str(sid_val)
        logger.debug("成功完成信義網頁端兩階段握手，取得 sat: %s, sid: %s", sat_str, sid_str)
        return SinyiWebSession(sat=sat_str, sid=sid_str)

    async def ensure_web_session(self, force_refresh: bool = False) -> SinyiWebSession:
        """取得或向信義網頁端換發有效之動態會話憑證 (sat 與 sid)

        採用雙重檢查鎖定 (Double-Checked Locking) 確保高併發下僅發起一次握手，
        並具備遠端連線異常時平滑回退至備用種子憑證之防禦機制。
        """
        # 第一次檢查 (無鎖高速路徑)
        if self._cached_web_session and not force_refresh:
            return self._cached_web_session

        async with self._web_session_lock:
            # 第二次檢查 (進入鎖後再次核實)
            if self._cached_web_session and not force_refresh:
                return self._cached_web_session

            try:
                client = await self.get_web_client()
                session = await self._perform_web_handshake(client)
                self._cached_web_session = session
                return self._cached_web_session
            except Exception as e:
                logger.warning("向信義網頁端請求兩階段 Session 握手失敗，回退至備用種子憑證: %s", e)

            # 握手失敗時平滑降級回退至已驗證之種子憑證
            self._cached_web_session = SinyiWebSession(
                sat=FALLBACK_SEED_WEB_SAT,
                sid=FALLBACK_SEED_WEB_SID,
            )
            return self._cached_web_session

    async def post_mobile_api(
        self,
        path: str,
        payload: Dict[str, Any],
        wrap_param: bool = True,
        merge_device_info: bool = True,
        headers: Optional[Dict[str, str]] = None,
        retry_on_invalid_sid: bool = True,
    ) -> Dict[str, Any]:
        """發送加密 POST 請求至信義房屋手機端網關並自動解密回應

        Args:
            path: API 端點路徑 (例如 "/filterObject.php", "/getObjectContent.php")。
            payload: 待發送之業務參數字典。
            wrap_param: 是否包裹為 {"param": "<B64>"}，預設 True。
            merge_device_info: 是否自動補足缺少的設備參數，預設 True。
            headers: 額外追加或覆蓋之標頭。
            retry_on_invalid_sid: 當收到 sid無效 (000991) 時是否自動換發重試，預設 True。

        Returns:
            解密後的業務資料字典 (retCode == "000000")。
        """
        full_url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        client = await self.get_mobile_client()

        # 1. 補齊設備與環境參數
        final_payload = dict(payload)
        if merge_device_info:
            for k, v in DEFAULT_DEVICE_PAYLOAD.items():
                if k not in final_payload:
                    final_payload[k] = v

        # 2. 加密 Request 酬載
        encrypted_body = self.crypto.encrypt_request_payload(
            final_payload, wrap_param=wrap_param
        )

        # 3. 確保擁有合法之有效 sid
        current_sid = await self.ensure_mobile_sid()
        req_headers: Dict[str, str] = {"sid": current_sid}
        if headers:
            req_headers.update(headers)

        # 4. 發送 HTTP POST
        try:
            response = await client.post(
                full_url,
                json=encrypted_body,
                headers=req_headers,
            )
        except httpx.ConnectTimeout as e:
            raise ProviderConnectionError("sinyi", f"連線至信義房屋逾時: {full_url}") from e
        except httpx.NetworkError as e:
            raise ProviderConnectionError("sinyi", f"信義房屋網路連線異常: {e}") from e

        # 5. HTTP 狀態碼檢驗
        if response.status_code == 429:
            raise RateLimitExceededError("sinyi", "觸發信義房屋請求頻率限制 (HTTP 429)")

        if response.status_code == 403:
            raise RateLimitExceededError("sinyi", "信義房屋存取被拒絕 (HTTP 403)，請確認標頭配置")

        if response.status_code != 200:
            raise ProviderResponseError("sinyi", f"信義房屋 HTTP 狀態碼異常: {response.status_code}")

        # 6. 解密 Response 酬載
        decrypted_data = self.crypto.decrypt_response_payload(response.text)

        # 7. 業務狀態碼檢驗 (含自動刷新過期 sid 機制)
        ret_code = decrypted_data.get("retCode")
        if ret_code is not None and str(ret_code) != "000000":
            ret_code_str = str(ret_code)
            ret_msg = decrypted_data.get("retMsg", "未知業務錯誤")

            # 遇到 sid無效 (000991) 自動換發重試一次
            if ret_code_str == "000991" and retry_on_invalid_sid:
                logger.info("信義房屋連線序號過期 (000991)，自動換發全新 sid 重試...")
                await self.ensure_mobile_sid(force_refresh=True)
                return await self.post_mobile_api(
                    path=path,
                    payload=payload,
                    wrap_param=wrap_param,
                    merge_device_info=merge_device_info,
                    headers=headers,
                    retry_on_invalid_sid=False,
                )

            raise ProviderResponseError(
                "sinyi", f"信義房屋 API 回應業務錯誤 [{ret_code_str}]: {ret_msg}"
            )

        return decrypted_data

    async def post_web_api(
        self,
        path: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        retry_on_invalid_token: bool = True,
    ) -> Dict[str, Any]:
        """發送請求至信義房屋網頁端 API 網關並自動解密回應

        自動注入動態握手憑證 (sat 與 sid)，並於遭遇認證 Token 錯誤 (308) 時自動重新握手重試。

        Args:
            path: API 端點路徑 (例如 "/searchCommunity.php", "/getCommunityContent.php")。
            payload: 業務參數字典。
            headers: 額外覆蓋之標頭。
            retry_on_invalid_token: 當收到憑證失效 (308) 時是否自動換發重試，預設 True。

        Returns:
            解密後之業務資料字典 (retCode == "200" 或 "000000")。
        """
        full_url = f"{self.web_base_url}{path}" if path.startswith("/") else f"{self.web_base_url}/{path}"
        client = await self.get_web_client()

        # 1. 補齊網頁端設備與環境指紋參數
        final_payload = dict(payload)
        for k, v in DEFAULT_WEB_DEVICE_PAYLOAD.items():
            if k not in final_payload:
                final_payload[k] = v

        # 2. 獲取動態 Session 憑證並注入標頭
        session = await self.ensure_web_session()
        req_headers: Dict[str, str] = {
            "sat": session.sat,
            "sid": session.sid,
        }
        if headers:
            req_headers.update(headers)

        # 3. 發送 HTTP POST (純 JSON 酬載)
        try:
            response = await client.post(
                full_url,
                json=final_payload,
                headers=req_headers,
            )
        except httpx.ConnectTimeout as e:
            raise ProviderConnectionError("sinyi", f"連線至信義房屋網頁端逾時: {full_url}") from e
        except httpx.NetworkError as e:
            raise ProviderConnectionError("sinyi", f"信義房屋網頁端網路連線異常: {e}") from e

        # 4. HTTP 狀態碼檢驗
        if response.status_code == 429:
            raise RateLimitExceededError("sinyi", "觸發信義房屋網頁端請求頻率限制 (HTTP 429)")

        if response.status_code == 403:
            raise RateLimitExceededError("sinyi", "信義房屋網頁端存取被拒絕 (HTTP 403)，請確認標頭配置")

        if response.status_code != 200:
            raise ProviderResponseError("sinyi", f"信義房屋網頁端 HTTP 狀態碼異常: {response.status_code}")

        # 5. 解密 Response 酬載
        decrypted_data = self.crypto.decrypt_response_payload(response.text)

        # 6. 業務狀態碼檢驗 (網頁端成功碼為 "200" 或 "000000"，過期代碼為 "308")
        ret_code = decrypted_data.get("retCode")
        if ret_code is not None:
            ret_code_str = str(ret_code)

            # 遇到認證 Token 錯誤 (308) 自動強制換發重試一次
            if ret_code_str == "308" and retry_on_invalid_token:
                logger.info("信義房屋網頁端憑證失效 (308)，自動重啟 Session 握手重試...")
                await self.ensure_web_session(force_refresh=True)
                return await self.post_web_api(
                    path=path,
                    payload=payload,
                    headers=headers,
                    retry_on_invalid_token=False,
                )

            if ret_code_str not in ("200", "000000"):
                ret_msg = decrypted_data.get("retMsg", "未知業務錯誤")
                raise ProviderResponseError(
                    "sinyi", f"信義房屋網頁端 API 回應業務錯誤 [{ret_code_str}]: {ret_msg}"
                )

        return decrypted_data

    async def close(self):
        """關閉連線池釋放資源"""
        if self._mobile_client and not self._mobile_client.is_closed:
            await self._mobile_client.aclose()
            self._mobile_client = None
        if self._web_client and not self._web_client.is_closed:
            await self._web_client.aclose()
            self._web_client = None
