"""HouseLensAPI - 信義房屋來源自主 API 診斷探針套件 (Sinyi Diagnostics Probe Suite)

定義信義房屋平台各 API 端點規格與自主探針，支援動態 ID 鏈接與種子回退。
涵蓋系統連線健康檢查 (SYSTEM) 與預留業務端點。
嚴禁任何裝飾性符號 (Emoji)。
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from src.core.diagnostics.recorder import DiagnosticTransportRecorder
from src.core.interfaces.diagnostics import IProbeEndpoint, IProviderDiagnostics
from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticDomain,
    DiagnosticMetadata,
    DiagnosticStatus,
    ProbeExecutionContext,
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

SEED_SALE_ID = "7342DG"  # 敦品苑全新舒適三房車位 (封包紀錄種子)
SEED_COMMUNITY_ID = "G0000316"  # 帝國花園 (封包紀錄社區種子)


class BaseSinyiProbe(IProbeEndpoint):
    """信義房屋探針基礎類別"""

    def __init__(self, context: Optional[Dict[str, str]] = None):
        self._context = context if context is not None else {}
        self._crypto = SinyiCryptoService()

    def _create_metadata_template(self) -> DiagnosticMetadata:
        """建立初始元數據物件"""
        return DiagnosticMetadata(
            provider_id="sinyi",
            provider_name="信義房屋 Sinyi Housing",
            endpoint_id=self.endpoint_id,
            domain=self.domain.value,
            name=self.name,
            description=self.description,
            status=DiagnosticStatus.SUCCESS,
            status_code=None,
            latency_ms=0.0,
            timestamp="",
            error_message=None,
        )

    def _build_encrypted_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """建立加密請求 JSON 實體 ({"param": "<B64>"})"""
        merged_payload = dict(DEFAULT_DEVICE_PAYLOAD)
        merged_payload.update(payload)
        return self._crypto.encrypt_request_payload(merged_payload, wrap_param=True)

    def _build_headers(self, context: Optional[ProbeExecutionContext] = None) -> Dict[str, str]:
        """組裝信義 App 專屬通訊標頭 (sid 序號支援回退或外部注入)"""
        sid = FALLBACK_SEED_MOBILE_SID
        if context and context.extra_headers and "sid" in context.extra_headers:
            sid = context.extra_headers["sid"]
        headers = {
            "user-agent": SINYI_USER_AGENT,
            "code": SINYI_HEADER_CODE,
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
            "sid": sid,
        }
        if context and context.extra_headers:
            headers.update(context.extra_headers)
        return headers

    def _build_web_body(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """建立網頁端請求 JSON 實體 (合併設備指紋)"""
        merged_payload = dict(DEFAULT_WEB_DEVICE_PAYLOAD)
        merged_payload.update(payload)
        return merged_payload

    def _build_web_headers(self, context: Optional[ProbeExecutionContext] = None) -> Dict[str, str]:
        """組裝網頁端專屬通訊標頭 (支援備用種子與外部動態注入)"""
        headers = dict(SINYI_WEB_BASE_HEADERS)
        headers["sat"] = FALLBACK_SEED_WEB_SAT
        headers["sid"] = FALLBACK_SEED_WEB_SID
        if context and context.extra_headers:
            headers.update(context.extra_headers)
        return headers


class SinyiHealthPingProbe(BaseSinyiProbe):
    """信義房屋通訊通道健康度探針"""

    @property
    def endpoint_id(self) -> str:
        return "health_ping"

    @property
    def name(self) -> str:
        return "通訊通道與加密健康度檢測"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.SYSTEM

    @property
    def description(self) -> str:
        return "發送輕量加密請求至信義房屋網關檢測通訊鏈路與加解密機制"

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        url = f"{SINYI_API_BASE_URL}/filterObject.php"
        ping_payload = {
            "page": 1,
            "pageCnt": 1,
            "sort": "default",
            "filter": {
                "retRange": ["100"],
                "retType": 2,
            },
        }
        body = self._build_encrypted_body(ping_payload)
        headers = self._build_headers(context)
        metadata = self._create_metadata_template()

        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="POST",
            url=url,
            body=body,
            headers=headers,
        )


class SinyiSaleListProbe(BaseSinyiProbe):
    """信義中古屋物件清單 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "sale_list"

    @property
    def name(self) -> str:
        return "中古屋物件清單 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.SALE

    @property
    def description(self) -> str:
        return "測試信義房屋手機端中古屋物件條件篩選端點連線與回傳密文結構"

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        url = f"{SINYI_API_BASE_URL}/filterObject.php"
        search_payload: Dict[str, Any] = {
            "page": 1,
            "pageCnt": 5,
            "sort": "default",
            "filter": {
                "floor": None,
                "retRange": ["100"],
                "retType": 2,
            },
        }
        if context and context.extra_params:
            search_payload.update(context.extra_params)

        body = self._build_encrypted_body(search_payload)
        headers = self._build_headers(context)
        metadata = self._create_metadata_template()

        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="POST",
            url=url,
            body=body,
            headers=headers,
        )


class SinyiSaleDetailProbe(BaseSinyiProbe):
    """信義中古屋物件詳情 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "sale_detail"

    @property
    def name(self) -> str:
        return "中古屋物件詳情資訊 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.SALE

    @property
    def description(self) -> str:
        return "測試信義房屋手機端物件完整規格詳情端點連線與回傳密文結構"

    @property
    def default_target_id(self) -> str:
        return SEED_SALE_ID

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        if context and context.target_id:
            target_id = context.target_id
        elif "last_sale_id" in self._context:
            target_id = self._context["last_sale_id"]
        else:
            target_id = self.default_target_id

        url = f"{SINYI_API_BASE_URL}/getObjectContent.php"
        detail_payload = {
            "houseNo": target_id,
            "showOff": 0,
        }
        body = self._build_encrypted_body(detail_payload)
        headers = self._build_headers(context)
        metadata = self._create_metadata_template()

        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="POST",
            url=url,
            body=body,
            headers=headers,
        )


class SinyiCommunityListProbe(BaseSinyiProbe):
    """信義社區清單與搜尋 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "community_list"

    @property
    def name(self) -> str:
        return "社區清單與搜尋 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.COMMUNITY

    @property
    def description(self) -> str:
        return "測試信義房屋網頁端社區檢索端點連線與回傳密文結構"

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        url = f"{SINYI_WEB_API_BASE_URL}/searchCommunity.php"
        search_payload: Dict[str, Any] = {
            "page": 1,
            "pageCnt": 5,
            "sort": "0",
            "filter": {
                "retType": 2,
                "retRange": ["100"],
            },
            "isReturnTotal": True,
        }
        if context and context.extra_params:
            search_payload.update(context.extra_params)

        body = self._build_web_body(search_payload)
        headers = self._build_web_headers(context)
        metadata = self._create_metadata_template()

        artifact = await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="POST",
            url=url,
            body=body,
            headers=headers,
        )

        if (
            artifact.metadata.status == DiagnosticStatus.SUCCESS
            and artifact.response
            and isinstance(artifact.response.body, dict)
        ):
            content = artifact.response.body.get("content") or {}
            items = content.get("object") or []
            if items and isinstance(items, list):
                first_id = items[0].get("commId")
                if first_id:
                    self._context["last_community_id"] = str(first_id).strip()

        return artifact


class SinyiCommunityDetailProbe(BaseSinyiProbe):
    """信義社區物件詳情 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "community_detail"

    @property
    def name(self) -> str:
        return "社區物件詳情資訊 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.COMMUNITY

    @property
    def description(self) -> str:
        return "測試信義房屋網頁端社區完整規格詳情端點連線與回傳密文結構"

    @property
    def default_target_id(self) -> str:
        return SEED_COMMUNITY_ID

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        if context and context.target_id:
            target_id = context.target_id
        elif "last_community_id" in self._context:
            target_id = self._context["last_community_id"]
        else:
            target_id = self.default_target_id

        url = f"{SINYI_WEB_API_BASE_URL}/getCommunityContent.php"
        detail_payload = {
            "commId": target_id,
        }
        body = self._build_web_body(detail_payload)
        headers = self._build_web_headers(context)
        metadata = self._create_metadata_template()

        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="POST",
            url=url,
            body=body,
            headers=headers,
        )


class SourceSinyiDiagnostics(IProviderDiagnostics):
    """信義房屋來源提供者診斷套件"""

    def __init__(self):
        self._shared_context: Dict[str, str] = {}
        self._probes: Dict[str, IProbeEndpoint] = {
            "health_ping": SinyiHealthPingProbe(self._shared_context),
            "sale_list": SinyiSaleListProbe(self._shared_context),
            "sale_detail": SinyiSaleDetailProbe(self._shared_context),
            "community_list": SinyiCommunityListProbe(self._shared_context),
            "community_detail": SinyiCommunityDetailProbe(self._shared_context),
        }

    @property
    def provider_id(self) -> str:
        return "sinyi"

    @property
    def provider_name(self) -> str:
        return "信義房屋 Sinyi Housing"

    def get_probes(self, domain: Optional[DiagnosticDomain] = None) -> List[IProbeEndpoint]:
        probes = list(self._probes.values())
        if domain is not None:
            return [p for p in probes if p.domain == domain]
        return probes

    def get_probe(self, endpoint_id: str) -> Optional[IProbeEndpoint]:
        return self._probes.get(endpoint_id)
