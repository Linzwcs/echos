# file: src/MuzaiCore/services/interfaces/__init__.py
from .ibase_service import IService
from .iediting_service import IEditingService
from .ihistory_service import IHistoryService
from .inode_service import INodeService
from .iproject_service import IProjectService
from .iquery_service import IQueryService
from .irouting_service import IRoutingService
from .isystem_service import ISystemService
from .itransport_service import ITransportService
from .ipersistence_service import IPersistenceService

__all__ = [
    "IService",
    "IEditingService",
    "IHistoryService",
    "INodeService",
    "IProjectService",
    "IQueryService",
    "IRoutingService",
    "ISystemService",
    "ITransportService",
    "IPersistenceService",
]
