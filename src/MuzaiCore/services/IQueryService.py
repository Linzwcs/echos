# file: src/MuzaiCore/services/IQueryService.py
from abc import ABC, abstractmethod
from typing import Optional
from .api_types import ToolResponse


class IQueryService(ABC):
    """A dedicated service for all read-only operations to inspect project state."""

    @abstractmethod
    def get_project_overview(self, project_id: str) -> ToolResponse:
        """Returns a high-level summary of the project (tempo, tracks, etc.)."""
        pass

    @abstractmethod
    def get_full_project_tree(self, project_id: str) -> ToolResponse:
        """Returns a detailed, hierarchical view of the entire project state."""
        pass

    @abstractmethod
    def find_node_by_name(self, project_id: str, name: str) -> ToolResponse:
        """Finds the first node (track, bus) that matches the given name."""
        pass

    @abstractmethod
    def get_node_details(self, project_id: str, node_id: str) -> ToolResponse:
        """Returns detailed information about a specific node (plugins, sends, params)."""
        pass

    @abstractmethod
    def get_connections_for_node(self, project_id: str,
                                 node_id: str) -> ToolResponse:
        """Returns all input and output connections for a given node."""
        pass

    @abstractmethod
    def get_parameter_value(self, project_id: str, node_id: str,
                            parameter_path: str) -> ToolResponse:
        """
        Gets the current value of a parameter, e.g., parameter_path='volume'
        or 'insert_0_cutoff'.
        """
        pass
