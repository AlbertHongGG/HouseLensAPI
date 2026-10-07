"""HouseLensAPI - 永慶房屋來源自主 API 診斷探針套件 (Yungching Diagnostics Probe Suite)

定義永慶平台各 API 端點規格與自主探針，支援動態 ID 鏈接與種子回退。
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
from src.providers.source_yungching.client import (
    DEFAULT_DEVICE_UID,
    DEFAULT_QUERY_PARAMS,
    DEFAULT_UNIVERSAL_ID,
    DEFAULT_USER_AGENT,
    YUNGCHING_BASE_URL,
)

logger = logging.getLogger(__name__)

DEFAULT_YUNGCHING_HEADERS: Dict[str, str] = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "deviceuid": DEFAULT_DEVICE_UID,
    "universalid": DEFAULT_UNIVERSAL_ID,
    "Accept-Encoding": "gzip",
}

SEED_COMMUNITY_ID = "43035"  # 全坤威峰


class BaseYungchingProbe(IProbeEndpoint):
    """永慶房屋探針基礎類別"""

    def __init__(self, context: Optional[Dict[str, str]] = None):
        self._context = context if context is not None else {}

    def _create_metadata_template(self) -> DiagnosticMetadata:
        """建立初始元數據物件"""
        return DiagnosticMetadata(
            provider_id="yungching",
            provider_name="永慶房產集團 永慶房仲網",
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

    def _merge_params(
        self,
        base_params: Dict[str, Any],
        context: Optional[ProbeExecutionContext],
    ) -> Dict[str, Any]:
        """合併預設參數與外部上下文提供之額外 Query 參數"""
        merged = dict(base_params)
        if context and context.extra_params:
            merged.update(context.extra_params)
        return merged

    def _merge_headers(
        self,
        base_headers: Dict[str, str],
        context: Optional[ProbeExecutionContext],
    ) -> Dict[str, str]:
        """合併預設標頭與外部上下文提供之自訂 HTTP 標頭"""
        merged = dict(base_headers)
        if context and context.extra_headers:
            merged.update(context.extra_headers)
        return merged


class YungchingCommunityListProbe(BaseYungchingProbe):
    """永慶社區清單 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "community_list"

    @property
    def name(self) -> str:
        return "社區物件清單 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.COMMUNITY

    @property
    def description(self) -> str:
        return "測試永慶房屋社區列表端點連線與回傳資料結構"

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        url = f"{YUNGCHING_BASE_URL}/v1/SearchCommunityList"
        params = self._merge_params(
            {
                "SearchMode": "1",
                "Sequence": "1",
                "Page": 1,
                "Limit": 5,
                "County": "台北市",
                **DEFAULT_QUERY_PARAMS,
            },
            context,
        )
        headers = self._merge_headers(DEFAULT_YUNGCHING_HEADERS, context)
        metadata = self._create_metadata_template()
        artifact = await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )

        # 動態提取社區 ID 供詳情探針使用
        if artifact.response and isinstance(artifact.response.body, dict):
            list_objs = artifact.response.body.get("Data", {}).get("ListObjects") or []
            for item in list_objs:
                if isinstance(item, dict) and item.get("ID"):
                    self._context["community_id"] = str(item["ID"])
                    break

        return artifact


class YungchingCommunityDetailProbe(BaseYungchingProbe):
    """永慶社區詳情 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "community_detail"

    @property
    def name(self) -> str:
        return "社區物件詳情 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.COMMUNITY

    @property
    def description(self) -> str:
        return "測試永慶房屋社區詳細資料規格與相簿結構"

    @property
    def requires_target_id(self) -> bool:
        return True

    @property
    def default_target_id(self) -> Optional[str]:
        return SEED_COMMUNITY_ID

    async def execute(
        self,
        client: httpx.AsyncClient,
        context: Optional[ProbeExecutionContext] = None,
    ) -> DiagnosticArtifact:
        target_id = None
        if context and context.target_id:
            target_id = context.target_id
        elif "community_id" in self._context:
            target_id = self._context["community_id"]
        else:
            target_id = self.default_target_id

        url = f"{YUNGCHING_BASE_URL}/v1/SearchCommunityDetail"
        params = self._merge_params(
            {
                "CommunityID": target_id,
                **DEFAULT_QUERY_PARAMS,
            },
            context,
        )
        headers = self._merge_headers(DEFAULT_YUNGCHING_HEADERS, context)
        metadata = self._create_metadata_template()
        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )


class SourceYungchingDiagnostics(IProviderDiagnostics):
    """永慶房屋來源提供者診斷套件"""

    def __init__(self):
        self._shared_context: Dict[str, str] = {}
        self._probes: Dict[str, IProbeEndpoint] = {
            "community_list": YungchingCommunityListProbe(self._shared_context),
            "community_detail": YungchingCommunityDetailProbe(self._shared_context),
        }

    @property
    def provider_id(self) -> str:
        return "yungching"

    @property
    def provider_name(self) -> str:
        return "永慶房產集團 永慶房仲網"

    def get_probes(self, domain: Optional[DiagnosticDomain] = None) -> List[IProbeEndpoint]:
        probes = list(self._probes.values())
        if domain is not None:
            return [p for p in probes if p.domain == domain]
        return probes

    def get_probe(self, endpoint_id: str) -> Optional[IProbeEndpoint]:
        return self._probes.get(endpoint_id)
