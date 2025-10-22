# file: src/MuzaiCore/services/__init__.py

# NOTE: This is a simplified facade for demonstration.
# In a real app, you would use dependency injection.
from ..interfaces import IDAWManager
# TODO: We should also create an IPluginRegistry interface
# from ..interfaces import IPluginRegistry


class DAWFacade:
    """Agent's single entry point to the DAW Core."""

    def __init__(self, manager: IDAWManager,
                 registry):  # registry should be IPluginRegistry
        from ..implementations.services import (ProjectService,
                                                TransportService, NodeService,
                                                RoutingService, EditingService,
                                                HistoryService)
        self.project = ProjectService(manager)
        self.transport = TransportService(manager)
        self.nodes = NodeService(manager, registry)
        self.routing = RoutingService(manager)
        self.editing = EditingService(manager)
        self.history = HistoryService(manager)
