# file: src/MuzaiCore/services/INodeService.py
from abc import ABC, abstractmethod
from typing import Optional
from MuzaiCore.models import ToolResponse
from .base_service import IService


class INodeService(IService):
    # --- Create ---
    @abstractmethod
    def create_instrument_track(self, project_id: str,
                                name: str) -> ToolResponse:
        pass

    @abstractmethod
    def create_audio_track(self, project_id: str, name: str) -> ToolResponse:
        pass

    @abstractmethod
    def create_bus_track(self, project_id: str, name: str) -> ToolResponse:
        pass

    @abstractmethod
    def create_vca_track(self, project_id: str, name: str) -> ToolResponse:
        pass

    # --- Modify ---
    @abstractmethod
    def delete_node(self, project_id: str, node_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def rename_node(self, project_id: str, node_id: str,
                    new_name: str) -> ToolResponse:
        pass

    @abstractmethod
    def add_insert_plugin(self,
                          project_id: str,
                          target_node_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None) -> ToolResponse:
        pass

    @abstractmethod
    def remove_insert_plugin(self, project_id: str, target_node_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:
        pass
