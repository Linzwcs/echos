# file: src/MuzaiCore/services/DAWFacade.py
from ..interfaces import IDAWManager

# Import all service interfaces
from .IProjectService import IProjectService
from .ITransportService import ITransportService
from .INodeService import INodeService
from .IRoutingService import IRoutingService
from .IEditingService import IEditingService
from .IHistoryService import IHistoryService
from .IQueryService import IQueryService  # <-- NEW: A dedicated service for reads
from .ISystemService import ISystemService  # <-- NEW: For system-level interactions

# Import concrete service implementations
from ..implementations.services import (ProjectService, TransportService,
                                        NodeService, RoutingService,
                                        EditingService, HistoryService,
                                        QueryService, SystemService)


class DAWFacade:
    """
    The single, unified API endpoint for an AI Agent to interact with the DAW Core.
    It provides a set of tools, organized by function, that operate on the underlying DAW.
    """

    def __init__(self, manager: IDAWManager):
        # The Facade is responsible for instantiating all the service classes (tools).
        # This is a form of dependency injection.
        self.project: IProjectService = ProjectService(manager)
        self.transport: ITransportService = TransportService(manager)
        self.nodes: INodeService = NodeService(manager)
        self.routing: IRoutingService = RoutingService(manager)
        self.editing: IEditingService = EditingService(manager)
        self.history: IHistoryService = HistoryService(manager)
        self.query: IQueryService = QueryService(
            manager)  # For all read operations
        self.system: ISystemService = SystemService(
            manager)  # For plugins, devices etc.

    def list_tools(self) -> dict:
        """Provides a manifest of available tool categories."""
        return {
            "project":
            "Tools for managing projects (create, load, save).",
            "transport":
            "Tools for controlling playback (play, stop, set tempo).",
            "nodes":
            "Tools for managing tracks and other nodes (create, delete).",
            "routing":
            "Tools for managing signal flow (connect, create sends).",
            "editing":
            "Tools for editing content (clips, notes, automation).",
            "history":
            "Tools for managing undo/redo history.",
            "query":
            "Tools for inspecting the state of the project.",
            "system":
            "Tools for interacting with system resources like plugins and devices."
        }
