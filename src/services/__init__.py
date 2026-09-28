"""HouseLensAPI - 服務層套件 (Services Package)"""

from src.services.aggregator import HouseAggregatorService
from src.services.deduplication import (
    DeduplicationResult,
    PropertyDeduplicationService,
    is_area_compatible,
    is_layout_compatible,
    normalize_floor,
)

__all__ = [
    "HouseAggregatorService",
    "PropertyDeduplicationService",
    "DeduplicationResult",
    "normalize_floor",
    "is_layout_compatible",
    "is_area_compatible",
]
