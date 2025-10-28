# file: src/MuzaiCore/interfaces/IRouter.py
from abc import ABC, abstractmethod
from typing import List

# +++ ADD THIS IMPORT +++
from .inode import INode

from ...models import Port, Connection


class IRouter(ABC):
    # +++ NEW METHODS +++
    @abstractmethod
    def add_node(self, node: INode):
        """Adds a node to the routing graph, initially without connections."""
        pass

    @abstractmethod
    def remove_node(self, node_id: str):
        """Removes a node and all its connections from the routing graph."""
        pass

    @abstractmethod
    def connect(self, source_port: Port, dest_port: Port) -> bool:
        pass

    @abstractmethod
    def get_processing_order(self) -> List[str]:
        """Returns a topologically sorted list of node IDs."""
        pass

    @abstractmethod
    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        pass
