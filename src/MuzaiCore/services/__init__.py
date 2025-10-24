"""
MuzaiCore Services Package
==========================

This package provides high-level services for interacting with the Muzai Digital
Audio Workstation (DAW) core. Each service encapsulates a specific area of
functionality, such as project management, node manipulation, audio routing,
and playback control.

These services are designed to be the primary interface for tools, user
interfaces, or external scripts to interact with the DAW's state in a structured
and safe manner.
"""

from .editing_service import EditingService
from .history_service import HistoryService
from .node_service import NodeService
from .project_service import ProjectService
from .query_service import QueryService
from .routing_service import RoutingService
from .system_service import SystemService
from .transport_service import TransportService

__all__ = [
    "EditingService",
    "HistoryService",
    "NodeService",
    "ProjectService",
    "QueryService",
    "RoutingService",
    "SystemService",
    "TransportService",
]
