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
    PageQuery,
    PageResult,
)
from src.domain.community import (
    CommunitySummary,
    CommunityDetail,
    CommunitySearchQuery,
)
from src.domain.sale_house import (
    SaleHouseSummary,
    SaleHouseDetail,
    SaleHouseSearchQuery,
)
from src.domain.new_house import (
    NewHouseLayoutItem,
    NewHouseSummary,
    NewHouseDetail,
    NewHouseSearchQuery,
)

__all__ = [
    "Region",
    "BuildingType",
    "NewHouseStatus",
    "AgeRange",
    "GeoPoint",
    "StructuredAddress",
    "PageQuery",
    "PageResult",
    "CommunitySummary",
    "CommunityDetail",
    "CommunitySearchQuery",
    "SaleHouseSummary",
    "SaleHouseDetail",
    "SaleHouseSearchQuery",
    "NewHouseLayoutItem",
    "NewHouseSummary",
    "NewHouseDetail",
    "NewHouseSearchQuery",
]
