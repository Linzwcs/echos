# file: src/MuzaiCore/interfaces/IPluginRegistry.py
from abc import ABC, abstractmethod
from typing import List, Optional

from ...models import PluginDescriptor


class IPluginRegistry(ABC):
    """
    Manages the discovery and retrieval of available plugin blueprints.
    """

    @abstractmethod
    def scan_for_plugins(self):
        """Scans the system for available plugins and populates the registry."""
        pass

    @abstractmethod
    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        """Gets a single plugin descriptor by its unique ID."""
        pass

    @abstractmethod
    def list_plugins(self) -> List[PluginDescriptor]:
        """Lists all available plugin descriptors."""
        pass
