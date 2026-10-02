"""HouseLensAPI - 591 來源自主 API 診斷探針套件 (591 Diagnostics Probe Suite)

定義 591 平台各 API 端點規格與自主探針，支援動態 ID 鏈接與種子回退。
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
)
from src.providers.source_591.client import (
    CANONICAL_DOMAINS,
    DEFAULT_APP_UA,
    DEFAULT_DEVICE_ID,
)

logger = logging.getLogger(__name__)

DEFAULT_591_HEADERS: Dict[str, str] = {
    "User-Agent": DEFAULT_APP_UA,
    "Accept": "application/json, text/plain, */*",
    "device": "android",
    "deviceid": DEFAULT_DEVICE_ID,
    "mobile_id": DEFAULT_DEVICE_ID,
    "version": "8.13.0.975",
    "loginvalid": "0",
}

DEFAULT_591_QUERY_PARAMS: Dict[str, Any] = {
    "mobile_id": DEFAULT_DEVICE_ID,
    "deviceid": DEFAULT_DEVICE_ID,
    "device_id": DEFAULT_DEVICE_ID,
    "version": "8.13.0.975",
    "device": "android",
}

# 預設種子 ID (回退用)
SEED_COMMUNITY_ID = "5855864"
SEED_SALE_ID = "20604856"
SEED_NEW_HOUSE_ID = "138045"


class Base591Probe(IProbeEndpoint):
    """591 探針基礎類別"""

    def __init__(self, context: Optional[Dict[str, str]] = None):
        self._context = context if context is not None else {}

    def _create_metadata_template(self) -> DiagnosticMetadata:
        """建立初始元數據物件"""
        return DiagnosticMetadata(
            provider_id="591",
            provider_name="數字科技 591 房屋交易",
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


class CommunityListProbe(Base591Probe):
    """社區物件清單 API 探針"""

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
        return "測試 591 社區列表端點連線與回傳資料結構"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        url = f"{CANONICAL_DOMAINS['market']}/v1/search/list"
        params = {
            "page": 1,
            "page_size": 5,
            "regionid": 1,
            "is_sale": 0,
            "post_type": "8,2",
            "cm91dGU": "L2NvbW11bml0eS9ob21l",
            **DEFAULT_591_QUERY_PARAMS,
        }
        metadata = self._create_metadata_template()
        artifact = await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=DEFAULT_591_HEADERS,
        )

        # 動態提取社區 ID 供詳情探針使用
        if artifact.response and isinstance(artifact.response.body, dict):
            items = (
                artifact.response.body.get("data", {}).get("items")
                or artifact.response.body.get("items")
                or []
            )
            for item in items:
                if isinstance(item, dict):
                    cid = item.get("id") or item.get("community_id")
                    if cid:
                        self._context["community_id"] = str(cid)
                        break

        return artifact


class CommunityDetailProbe(Base591Probe):
    """社區詳細資訊 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "community_detail"

    @property
    def name(self) -> str:
        return "社區詳細資訊 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.COMMUNITY

    @property
    def description(self) -> str:
        return "測試 591 單一社區完整資料端點連線 (支援動態 ID 與種子回退)"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        target_id = self._context.get("community_id", SEED_COMMUNITY_ID)
        url = f"{CANONICAL_DOMAINS['market']}/v1/app/gateway/community/info"
        params = {
            "id": target_id,
            "cm91dGU": "L2NvbW11bml0eS9kZXRhaWw=",
            **DEFAULT_591_QUERY_PARAMS,
        }
        headers = dict(DEFAULT_591_HEADERS)
        headers["cm91dgu"] = "L2NvbW11bml0eS9kZXRhaWw="
        metadata = self._create_metadata_template()
        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )


class SaleHouseListProbe(Base591Probe):
    """中古屋物件清單 API 探針"""

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
        return "測試 591 中古屋多條件列表端點連線與回傳資料結構"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        url = f"{CANONICAL_DOMAINS['house']}/v1/app/gateway/sale/list"
        params = {
            "searchtype": "1",
            "type": "sale",
            "news": "3",
            "newlist": "1",
            "flutter_page": "1",
            "category": "1",
            "module": "iphone",
            "action": "houseRsList",
            "regionid": 1,
            "p": 1,
            "kind": 0,
            "o": "90",
            "cm91dGU": "L3NhbGVob3VzZS9saXN0",
            **DEFAULT_591_QUERY_PARAMS,
        }
        headers = dict(DEFAULT_591_HEADERS)
        headers["cm91dgu"] = "L3NhbGVob3VzZS9saXN0"
        metadata = self._create_metadata_template()
        artifact = await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )

        # 動態提取中古屋 ID 供詳情探針使用
        if artifact.response and isinstance(artifact.response.body, dict):
            items = (
                artifact.response.body.get("data", {}).get("items")
                or artifact.response.body.get("items")
                or []
            )
            for item in items:
                if isinstance(item, dict):
                    raw_id = item.get("houseid") or item.get("id") or item.get("house_id")
                    if raw_id:
                        clean_id = str(raw_id).lstrip("S").lstrip("H")
                        self._context["sale_id"] = clean_id
                        break

        return artifact


class SaleHouseDetailProbe(Base591Probe):
    """中古屋詳細資訊 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "sale_detail"

    @property
    def name(self) -> str:
        return "中古屋詳細資訊 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.SALE

    @property
    def description(self) -> str:
        return "測試 591 中古屋物件詳情端點連線 (支援動態 ID 與種子回退)"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        target_id = self._context.get("sale_id", SEED_SALE_ID)
        url = f"{CANONICAL_DOMAINS['house']}/v1/app/gateway/sale/detail"
        params = {
            "id": target_id,
            "cm91dGU": "L3NhbGVob3VzZS9kZXRhaWw=",
            **DEFAULT_591_QUERY_PARAMS,
        }
        headers = dict(DEFAULT_591_HEADERS)
        headers["cm91dgu"] = "L3NhbGVob3VzZS9kZXRhaWw="
        metadata = self._create_metadata_template()
        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )


class NewHouseListProbe(Base591Probe):
    """新建案物件清單 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "new_house_list"

    @property
    def name(self) -> str:
        return "新建案物件清單 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.NEW_HOUSE

    @property
    def description(self) -> str:
        return "測試 591 新建案列表端點連線與回傳結構"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        url = f"{CANONICAL_DOMAINS['newhouse']}/v1/list-search"
        params = {
            "regionid": 1,
            "searchtype": 1,
            "p": 1,
            "limit": 5,
            "cm91dGU": "L25ld2hvdXNlL2hvdXNpbmdsaXN0",
            **DEFAULT_591_QUERY_PARAMS,
        }
        headers = dict(DEFAULT_591_HEADERS)
        headers["cm91dgu"] = "L25ld2hvdXNlL2hvdXNpbmdsaXN0"
        metadata = self._create_metadata_template()
        artifact = await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )

        # 動態提取新建案 HID 供詳情探針使用
        if artifact.response and isinstance(artifact.response.body, dict):
            items = (
                artifact.response.body.get("data", {}).get("items")
                or artifact.response.body.get("items")
                or []
            )
            for item in items:
                if isinstance(item, dict):
                    hid = item.get("hid") or item.get("id")
                    if hid:
                        self._context["new_house_id"] = str(hid)
                        break

        return artifact


class NewHouseDetailProbe(Base591Probe):
    """新建案詳細資訊 API 探針"""

    @property
    def endpoint_id(self) -> str:
        return "new_house_detail"

    @property
    def name(self) -> str:
        return "新建案詳細資訊 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.NEW_HOUSE

    @property
    def description(self) -> str:
        return "測試 591 新建案規格詳情端點連線 (支援動態 ID 與種子回退)"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        target_id = self._context.get("new_house_id", SEED_NEW_HOUSE_ID)
        url = f"{CANONICAL_DOMAINS['newhouse']}/v1/detail/base-info"
        params = {
            "id": target_id,
            "short_video": 1,
            "cm91dGU": "L25ld2hvdXNlL2hvdXNpbmdkZXRhaWw=",
            **DEFAULT_591_QUERY_PARAMS,
        }
        headers = dict(DEFAULT_591_HEADERS)
        headers["cm91dgu"] = "L25ld2hvdXNlL2hvdXNpbmdkZXRhaWw="
        metadata = self._create_metadata_template()
        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )


class HealthPingProbe(Base591Probe):
    """平台輕量健康檢測探針"""

    @property
    def endpoint_id(self) -> str:
        return "health_ping"

    @property
    def name(self) -> str:
        return "平台連線檢測 API"

    @property
    def domain(self) -> DiagnosticDomain:
        return DiagnosticDomain.SYSTEM

    @property
    def description(self) -> str:
        return "發送極輕量查詢檢測 591 伺服器通道通訊狀態"

    async def execute(self, client: httpx.AsyncClient) -> DiagnosticArtifact:
        url = f"{CANONICAL_DOMAINS['market']}/v1/search/list"
        params = {
            "page": 1,
            "page_size": 1,
            "regionid": 1,
        }
        metadata = self._create_metadata_template()
        return await DiagnosticTransportRecorder.capture(
            client=client,
            metadata=metadata,
            method="GET",
            url=url,
            params=params,
            headers=DEFAULT_591_HEADERS,
        )


class Source591Diagnostics(IProviderDiagnostics):
    """591 來源外掛專屬診斷套件實作"""

    def __init__(self):
        self._shared_context: Dict[str, str] = {}

    @property
    def provider_id(self) -> str:
        return "591"

    @property
    def provider_name(self) -> str:
        return "數字科技 591 房屋交易"

    def get_probes(self, domain: Optional[DiagnosticDomain] = None) -> List[IProbeEndpoint]:
        """按推薦之循序調用順序傳回探針清單 (清單優先於詳情以利動態擷取)"""
        ctx = self._shared_context
        all_probes: List[IProbeEndpoint] = [
            HealthPingProbe(ctx),
            CommunityListProbe(ctx),
            CommunityDetailProbe(ctx),
            SaleHouseListProbe(ctx),
            SaleHouseDetailProbe(ctx),
            NewHouseListProbe(ctx),
            NewHouseDetailProbe(ctx),
        ]
        if domain is None:
            return all_probes

        return [probe for probe in all_probes if probe.domain == domain]
