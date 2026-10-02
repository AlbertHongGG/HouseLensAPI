"""HouseLensAPI - 領域模型導出包 (Domain Package)"""

from src.domain.enums import (
    Region,
    BuildingType,
    NewHouseStatus,
    AgeRange,
)
from src.domain.common import (
    BaseSearchQuery,
    GeoPoint,
    PageQuery,
    PageResult,
    StructuredAddress,
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

from src.domain.diagnostics import (
    DiagnosticStatus,
    DiagnosticDomain,
    DiagnosticMetadata,
    DiagnosticRequestSnapshot,
    DiagnosticResponseSnapshot,
    DiagnosticArtifact,
    DiagnosticRunSummary,
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
    "BaseSearchQuery",
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
    "DiagnosticStatus",
    "DiagnosticDomain",
    "DiagnosticMetadata",
    "DiagnosticRequestSnapshot",
    "DiagnosticResponseSnapshot",
    "DiagnosticArtifact",
    "DiagnosticRunSummary",
]

