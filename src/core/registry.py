"""HouseLensAPI - 來源提供者動態註冊中心 (Provider Registry)

借鑑 ComicMgr 之 ProviderRegistry 模式，支援來源模組註冊、別名解析、動態探索與工廠實例化。
"""

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from src.core.exceptions import ProviderError, ProviderNotFoundError
from src.core.interfaces.provider import IHouseSourceProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """中央資料來源註冊中心 (Registry & Factory)"""

    def __init__(self):
        self._provider_classes: Dict[str, Type[IHouseSourceProvider]] = {}
        self._instances: Dict[str, IHouseSourceProvider] = {}
        self._aliases: Dict[str, str] = {}

    def register(
        self,
        provider_id: str,
        provider_cls: Type[IHouseSourceProvider],
        aliases: Optional[List[str]] = None,
    ):
        """註冊來源提供者類別"""
        if not issubclass(provider_cls, IHouseSourceProvider):
            raise ProviderError(provider_id, f"類別 '{provider_cls.__name__}' 未實作 IHouseSourceProvider")

        if provider_id in self._provider_classes:
            raise ProviderError(provider_id, f"Provider ID 衝突: '{provider_id}' 已註冊")

        self._provider_classes[provider_id] = provider_cls

        if aliases:
            for alias in aliases:
                if alias in self._provider_classes or alias in self._aliases:
                    raise ProviderError(provider_id, f"別名衝突: '{alias}' 已被使用")
                self._aliases[alias] = provider_id

        logger.info("已註冊 Provider: %s (別名: %s)", provider_id, aliases or [])

    def register_instance(self, provider: IHouseSourceProvider, aliases: Optional[List[str]] = None):
        """直接註冊已實例化的 Provider"""
        if not isinstance(provider, IHouseSourceProvider):
            raise ProviderError(getattr(provider, "provider_id", "unknown"), "實例未實作 IHouseSourceProvider")

        pid = provider.provider_id
        self._instances[pid] = provider
        self._provider_classes[pid] = type(provider)

        if aliases:
            for alias in aliases:
                self._aliases[alias] = pid

    def resolve_id(self, provider_id: str) -> str:
        """解析別名為標準主要 Provider ID"""
        if provider_id in self._provider_classes or provider_id in self._instances:
            return provider_id
        if provider_id in self._aliases:
            return self._aliases[provider_id]
        raise ProviderNotFoundError(provider_id)

    def get_provider(self, provider_id: str) -> IHouseSourceProvider:
        """取得指定 Provider 實例 (延遲實例化並快取)"""
        primary_id = self.resolve_id(provider_id)
        if primary_id not in self._instances:
            cls = self._provider_classes[primary_id]
            self._instances[primary_id] = cls()
        return self._instances[primary_id]

    def list_providers(self) -> List[str]:
        """列出所有已註冊的來源代碼"""
        return list(self._provider_classes.keys())

    def unregister(self, provider_id: str):
        """註銷指定的來源提供者"""
        primary_id = self.resolve_id(provider_id)
        self._provider_classes.pop(primary_id, None)
        self._instances.pop(primary_id, None)
        # 清除別名
        aliases_to_remove = [k for k, v in self._aliases.items() if v == primary_id]
        for a in aliases_to_remove:
            self._aliases.pop(a, None)

    def auto_discover(self):
        """自動掃描並載入 src/providers/ 目錄下的所有來源模組"""
        providers_dir = Path(__file__).parent.parent / "providers"
        if not providers_dir.exists() or not providers_dir.is_dir():
            return

        for item in providers_dir.iterdir():
            if item.is_dir() and not item.name.startswith(("_", ".")):
                module_name = f"src.providers.{item.name}.provider"
                try:
                    importlib.import_module(module_name)
                    logger.info("自動探索並載入模組: %s", module_name)
                except ModuleNotFoundError:
                    logger.debug("模組 %s 不存在或未定義 provider.py，略過", module_name)
                except Exception as e:
                    logger.warning("載入來源模組 %s 時發生異常: %s", module_name, e)


# 全域單例註冊中心
registry = ProviderRegistry()
