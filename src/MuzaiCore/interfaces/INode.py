# file: src/MuzaiCore/interfaces/INode.py
from abc import ABC, abstractmethod
from typing import List, Optional

from .IAudioProcessor import IAudioProcessor
from ..models import Port


class INode(IAudioProcessor, ABC):

    @property
    @abstractmethod
    def node_id(self) -> str:
        pass

    @abstractmethod
    def get_ports(self, port_type: Optional[str] = None) -> List[Port]:
        pass
