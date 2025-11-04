# file: src/MuzaiCore/services/IRoutingService.py
from abc import ABC, abstractmethod
from echos.models import ToolResponse
from .ibase_service import IService


class IRoutingService(IService):

    @abstractmethod
    def connect(self, project_id: str, source_node_id: str,
                source_port_id: str, dest_node_id: str,
                dest_port_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def disconnect(self, project_id: str, source_node_id: str,
                   dest_node_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def list_connections(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def create_send(self,
                    project_id: str,
                    source_track_id: str,
                    dest_bus_id: str,
                    is_post_fader: bool = True) -> ToolResponse:
        pass
