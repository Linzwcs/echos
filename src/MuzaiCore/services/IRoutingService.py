# file: src/MuzaiCore/services/IRoutingService.py
from abc import ABC, abstractmethod
from .api_types import ToolResponse

class IRoutingService(ABC):
    @abstractmethod
    def connect(self, project_id: str, source_node_id: str, source_port_id: str, dest_node_id: str, dest_port_id: str) -> ToolResponse: pass
