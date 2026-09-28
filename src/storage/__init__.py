"""HouseLensAPI - 持久化層套件 (Storage Package)"""

from src.storage.database import DatabaseManager, db_manager
from src.storage.interfaces import (
    ICommunityRepository,
    INewHouseRepository,
    IPropertyRepository,
)
from src.storage.models import (
    Base,
    CommunityTable,
    NewHouseTable,
    PropertyListingTable,
    PropertyTable,
)
from src.storage.repositories import (
    CommunityRepository,
    NewHouseRepository,
    PropertyRepository,
)

__all__ = [
    "DatabaseManager",
    "db_manager",
    "Base",
    "CommunityTable",
    "PropertyTable",
    "PropertyListingTable",
    "NewHouseTable",
    "ICommunityRepository",
    "IPropertyRepository",
    "INewHouseRepository",
    "CommunityRepository",
    "PropertyRepository",
    "NewHouseRepository",
]
