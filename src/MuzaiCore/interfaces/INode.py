# file: src/MuzaiCore/interfaces/INode.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ..subsystems.routing.routing_types import Port
from .IAudioProcessor import IAudioProcessor

class INode(IAudioProcessor, ABC):
    @property
    @abstractmethod
    def node_id(self) -> str: pass

    @abstractmethod
    def get_ports(self, port_type: Optional[str] = None) -> List[Port]: pass
