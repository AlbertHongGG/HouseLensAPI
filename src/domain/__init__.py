"""HouseLensAPI - 領域模型導出包 (Domain Package)"""

from src.domain.enums import (
    Region,
    BuildingType,
    NewHouseStatus,
    AgeRange,
)
from src.domain.common import (
    GeoPoint,
    StructuredAddress,
    PageResult,
)
from src.domain.community import (
    NormalizedCommunitySummary,
    NormalizedCommunityDetail,
    CommunitySearchQuery,
)
from src.domain.sale_house import (
    NormalizedSaleListing,
    NormalizedSalePropertyDetail,
    SaleHouseSearchQuery,
)
from src.domain.new_house import (
    NewHouseLayoutSpec,
    NormalizedNewHouseSummary,
    NormalizedNewHouseDetail,
    NewHouseSearchQuery,
)

__all__ = [
    "Region",
    "BuildingType",
    "NewHouseStatus",
    "AgeRange",
    "GeoPoint",
    "StructuredAddress",
    "PageResult",
    "NormalizedCommunitySummary",
    "NormalizedCommunityDetail",
    "CommunitySearchQuery",
    "NormalizedSaleListing",
    "NormalizedSalePropertyDetail",
    "SaleHouseSearchQuery",
    "NewHouseLayoutSpec",
    "NormalizedNewHouseSummary",
    "NormalizedNewHouseDetail",
    "NewHouseSearchQuery",
]

