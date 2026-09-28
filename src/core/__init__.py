"""HouseLensAPI - 核心基礎設施與介面包 (Core Package)"""

from src.core.exceptions import (
    HouseLensError,
    ProviderError,
    ProviderNotFoundError,
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitExceededError,
    ResourceNotFoundError,
)
from src.core.interfaces import (
    IHouseSourceProvider,
    ICommunityProvider,
    ISaleHouseProvider,
    INewHouseProvider,
)
from src.core.registry import ProviderRegistry, registry

__all__ = [
    "HouseLensError",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderConnectionError",
    "ProviderResponseError",
    "RateLimitExceededError",
    "ResourceNotFoundError",
    "IHouseSourceProvider",
    "ICommunityProvider",
    "ISaleHouseProvider",
    "INewHouseProvider",
    "ProviderRegistry",
    "registry",
]
