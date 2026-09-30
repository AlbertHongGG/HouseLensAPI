"""HouseLensAPI - HTTP 流量錄製與診斷引擎 (Diagnostic Traffic Recorder)

非侵入式雙向攔截 HTTP 請求與回應，精確計時並提取完整快照，包含敏感標頭脫敏與例外捕捉。
嚴禁任何裝飾性符號 (Emoji)。
"""

import datetime
import json
import logging
import time
from typing import Any, Dict, Optional
import httpx

from src.domain.diagnostics import (
    DiagnosticArtifact,
    DiagnosticMetadata,
    DiagnosticRequestSnapshot,
    DiagnosticResponseSnapshot,
    DiagnosticStatus,
)

logger = logging.getLogger(__name__)

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-auth-token",
    "token",
    "access-token",
    "api-key",
    "secret",
}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """將敏感標頭數值進行脫敏遮蔽"""
    sanitized: Dict[str, str] = {}
    for key, val in headers.items():
        if key.lower() in SENSITIVE_HEADER_KEYS:
            sanitized[key] = "***"
        else:
            sanitized[key] = val
    return sanitized


class DiagnosticTransportRecorder:
    """診斷專用 HTTP 流量錄製引擎

    提供高精確度耗時測量、請求與回應封包提取、脫敏與例外容錯捕捉。
    """

    @staticmethod
    async def capture(
        client: httpx.AsyncClient,
        metadata: DiagnosticMetadata,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
    ) -> DiagnosticArtifact:
        """執行 HTTP 請求並錄製完整的 DiagnosticArtifact 快照

        Args:
            client: 用於發送請求的 AsyncClient 實例
            metadata: 端點元數據範本 (將根據執行結果回填 status, latency_ms, status_code, error)
            method: HTTP 動詞 (GET, POST 等)
            url: 目標完整連線網址
            params: Query 參數字典
            headers: 額外自訂標頭 (與 client 標頭合併)
            body: 請求主體 (字典將以 JSON 發送，字串將以 text 發送)

        Returns:
            DiagnosticArtifact: 包含 metadata、request 快照與 response 快照之實體
        """
        now_iso = datetime.datetime.now().astimezone().isoformat()
        metadata.timestamp = now_iso

        # 整理要記錄的請求標頭 (合併 client 標頭與額外 headers)
        merged_headers: Dict[str, str] = dict(client.headers)
        if headers:
            merged_headers.update(headers)
        sanitized_request_headers = sanitize_headers(merged_headers)

        request_snapshot = DiagnosticRequestSnapshot(
            method=method.upper(),
            url=url,
            headers=sanitized_request_headers,
            params=params or {},
            body=body,
        )

        start_time = time.perf_counter()
        try:
            kwargs: Dict[str, Any] = {
                "params": params,
                "headers": headers,
            }
            if body is not None:
                if isinstance(body, (dict, list)):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = str(body)

            response = await client.request(method=method, url=url, **kwargs)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 解析回應內容
            sanitized_response_headers = sanitize_headers(dict(response.headers))
            parsed_body: Optional[Any] = None
            try:
                parsed_body = response.json()
            except Exception:
                parsed_body = response.text if response.text else None

            response_snapshot = DiagnosticResponseSnapshot(
                status_code=response.status_code,
                latency_ms=duration_ms,
                headers=sanitized_response_headers,
                body=parsed_body,
            )

            # 判定狀態
            metadata.status_code = response.status_code
            metadata.latency_ms = duration_ms

            if 200 <= response.status_code < 300:
                metadata.status = DiagnosticStatus.SUCCESS
                metadata.error_message = None
            else:
                metadata.status = DiagnosticStatus.HTTP_ERROR
                preview = str(parsed_body)[:200] if parsed_body else ""
                metadata.error_message = f"HTTP {response.status_code}: {preview}"

            return DiagnosticArtifact(
                metadata=metadata,
                request=request_snapshot,
                response=response_snapshot,
            )

        except httpx.TimeoutException as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metadata.status = DiagnosticStatus.TIMEOUT
            metadata.latency_ms = duration_ms
            metadata.status_code = None
            metadata.error_message = f"連線逾時: {type(exc).__name__} - {str(exc)}"
            return DiagnosticArtifact(
                metadata=metadata,
                request=request_snapshot,
                response=None,
            )

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metadata.status = DiagnosticStatus.NETWORK_ERROR
            metadata.latency_ms = duration_ms
            metadata.status_code = None
            metadata.error_message = f"網路連線異常: {type(exc).__name__} - {str(exc)}"
            return DiagnosticArtifact(
                metadata=metadata,
                request=request_snapshot,
                response=None,
            )

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metadata.status = DiagnosticStatus.PARSING_ERROR
            metadata.latency_ms = duration_ms
            metadata.status_code = None
            metadata.error_message = f"未預期例外: {type(exc).__name__} - {str(exc)}"
            return DiagnosticArtifact(
                metadata=metadata,
                request=request_snapshot,
                response=None,
            )
