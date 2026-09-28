"""HouseLensAPI - 核心例外體系 (Core Exceptions)

定義標準階層式例外，區分來源異常、網路異常、配額限制與實體未查獲。
"""

from typing import Optional


class HouseLensError(Exception):
    """HouseLensAPI 頂層例外基類"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProviderError(HouseLensError):
    """資料來源 Provider 處理異常基類"""

    def __init__(self, provider_id: str, message: str, details: Optional[dict] = None):
        super().__init__(f"[{provider_id}] {message}", details)
        self.provider_id = provider_id


class ProviderNotFoundError(HouseLensError):
    """未註冊或找不到指定的 Provider"""

    def __init__(self, provider_id: str):
        super().__init__(f"未找到已註冊的來源 Provider: '{provider_id}'")
        self.provider_id = provider_id


class ProviderConnectionError(ProviderError):
    """來源連線逾時或網路不可達"""
    pass


class ProviderResponseError(ProviderError):
    """來源回應格式不符合預期或狀態碼錯誤"""
    pass


class RateLimitExceededError(ProviderError):
    """觸發來源平台請求頻率限制 (429 / 阻擋)"""
    pass


class ResourceNotFoundError(HouseLensError):
    """指定的社區、房屋或建案實體不存在"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} 不存在: '{resource_id}'")
        self.resource_type = resource_type
        self.resource_id = resource_id
