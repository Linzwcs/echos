from abc import ABC, abstractmethod
from typing import Optional
from echos.models import ToolResponse
from .ibase_service import IService


class ITrackService(IService):

    @abstractmethod
    def create_instrument_track(
        self,
        project_id: str,
        name: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def create_audio_track(
        self,
        project_id: str,
        name: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def create_bus_track(
        self,
        project_id: str,
        name: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def create_vca_track(
        self,
        project_id: str,
        name: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def delete_track(
        self,
        project_id: str,
        node_id: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def rename_track(
        self,
        project_id: str,
        node_id: str,
        new_name: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def add_insert_plugin(
        self,
        project_id: str,
        target_node_id: str,
        plugin_unique_id: str,
        index: Optional[int] = None,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def remove_insert_plugin(
        self,
        project_id: str,
        target_node_id: str,
        plugin_instance_id: str,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def list_nodes(
        self,
        project_id: str,
        node_type: Optional[str] = None,
    ) -> ToolResponse:
        pass
