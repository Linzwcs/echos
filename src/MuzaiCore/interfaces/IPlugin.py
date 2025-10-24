# file: src/MuzaiCore/interfaces/IPlugin.py
from abc import ABC, abstractmethod
from .INode import INode


class IPlugin(INode, ABC):
    # IPlugin inherits node_id and process_block from INode
    @abstractmethod
    def get_latency_samples(self) -> int:
        """Returns the processing latency introduced by the plugin in samples."""
        pass
