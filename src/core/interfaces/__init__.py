"""HouseLensAPI - 核心抽象介面包 (Core Interfaces)"""

from src.core.interfaces.provider import IHouseSourceProvider
from src.core.interfaces.community import ICommunityProvider
from src.core.interfaces.sale_house import ISaleHouseProvider
from src.core.interfaces.new_house import INewHouseProvider
from src.core.interfaces.diagnostics import IProbeEndpoint, IProviderDiagnostics

__all__ = [
    "IHouseSourceProvider",
    "ICommunityProvider",
    "ISaleHouseProvider",
    "INewHouseProvider",
    "IProbeEndpoint",
    "IProviderDiagnostics",
]
