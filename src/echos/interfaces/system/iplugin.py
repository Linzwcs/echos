from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from .ilifecycle import ILifecycleAware
from .iparameter import IParameter
from .iserializable import ISerializable
from ...models import PluginDescriptor, CachedPluginInfo, PluginScanResult


class IPlugin(
        ILifecycleAware,
        ISerializable,
        ABC,
):

    @property
    @abstractmethod
    def descriptor(self) -> 'PluginDescriptor':
        pass

    @property
    @abstractmethod
    def plugin_instance_id(self) -> str:
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
        pass


class IPluginCache(ABC):

    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def persist(self) -> None:
        pass

    @abstractmethod
    def get_valid_entry(self, path: Path) -> Optional[CachedPluginInfo]:
        pass

    @abstractmethod
    def store_entry(self, path: Path, info: CachedPluginInfo) -> None:
        pass

    @abstractmethod
    def get_all_cached_paths(self) -> List[Path]:
        pass

    @abstractmethod
    def remove_entry(self, path: Path) -> None:
        pass


class IPluginRegistry(ABC):

    @abstractmethod
    def __init__(self, cache: IPluginCache):
        pass

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def update(self, force_rescan: bool = False):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def list_all(self) -> List[PluginDescriptor]:
        pass

    @abstractmethod
    def find_by_id(self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        pass

    @abstractmethod
    def find_by_path(self, path: str) -> Optional[PluginDescriptor]:
        pass


class IPluginInstanceManager(ABC):

    @abstractmethod
    def __init__(self, registry: IPluginRegistry):
        pass

    @abstractmethod
    def create_instance(
        self,
        plugin_instance_id: str,
        unique_plugin_id: str,
    ) -> Optional[Tuple[str, Any]]:
        pass

    @abstractmethod
    def get_instance(self, instance_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def release_instance(self, instance_id: str) -> bool:
        pass

    @abstractmethod
    def release_all(self) -> None:
        pass


class IPluginScanner(ABC):

    @abstractmethod
    def scan_plugin_paths(self, paths: List[Path]) -> List[Path]:
        pass

    @abstractmethod
    def scan_plugin_safe(self, plugin_path: Path) -> PluginScanResult:
        pass

    @abstractmethod
    def get_default_search_paths(self) -> List[Path]:
        pass
