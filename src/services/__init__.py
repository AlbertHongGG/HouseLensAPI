"""HouseLensAPI - 服務層套件 (Services Package)"""

from src.services.aggregator import HouseAggregatorService
from src.services.deduplication import (
    DeduplicationResult,
    PropertyDeduplicationService,
    is_area_compatible,
)

__all__ = [
    "HouseAggregatorService",
    "PropertyDeduplicationService",
    "DeduplicationResult",
    "is_area_compatible",
]

