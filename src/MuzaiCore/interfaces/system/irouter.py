# file: src/MuzaiCore/interfaces/IRouter.py
from abc import ABC, abstractmethod
from typing import List

# +++ ADD THIS IMPORT +++
from .inode import INode

from ...models import Port, Connection

# file: src/MuzaiCore/interfaces/system/irouter.py
from abc import ABC, abstractmethod
from typing import List

from .inode import INode
from .isync import IGraphSync  # <-- Import the new listener interface
from ...models import Port, Connection


class IRouter(ABC):
    # --- NEW: Subscription Methods ---
    @abstractmethod
    def subscribe(self, listener: IGraphSync):
        """Registers a listener for graph change events."""
        pass

    @abstractmethod
    def unsubscribe(self, listener: IGraphSync):
        """Unregisters a listener."""
        pass

    # --- Existing Methods ---
    @abstractmethod
    def add_node(self, node: INode):
        pass

    @abstractmethod
    def remove_node(self, node_id: str):
        pass

    @abstractmethod
    def connect(self, source_port: Port, dest_port: Port) -> bool:
        pass

    @abstractmethod
    def disconnect(self, source_port: Port, dest_port: Port) -> bool:
        pass

    @abstractmethod
    def get_processing_order(self) -> List[str]:
        pass

    @abstractmethod
    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        pass

    @abstractmethod
    def get_all_connections(self) -> List[Connection]:
        pass
