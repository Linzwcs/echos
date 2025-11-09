from typing import Any, Dict, List, Optional, Union
import uuid
from pathlib import Path
import json
from dataclasses import asdict

from echos.interfaces.system import IPluginRegistry
from .parameter import Parameter
from ..interfaces.system import IPlugin, IParameter, IEventBus, IPluginCache
from ..models import PluginDescriptor, Port, CachedPluginInfo, PluginDescriptor
from ..models.event_model import PluginEnabledChanged
from ..models.state_model import PluginState


class Plugin(IPlugin):

    def __init__(self,
                 descriptor: PluginDescriptor,
                 event_bus: IEventBus,
                 plugin_instance_id: Optional[str] = None):
        super().__init__()
        self._plugin_instance_id = plugin_instance_id or f"plugin_{uuid.uuid4()}"
        self._descriptor = descriptor
        self._event_bus = event_bus
        self._is_enabled = True
        self._parameters: Dict[str, IParameter] = {
            name:
            Parameter(
                owner_node_id=self._plugin_instance_id,
                name=name,
                default_value=default_value,
            )
            for name, default_value in descriptor.default_parameters.items()
        }

    @property
    def descriptor(self):
        return self._descriptor

    @property
    def plugin_instance_id(self) -> str:
        return self._plugin_instance_id

    @property
    def node_type(self) -> str:
        return "Plugin"

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool):
        if self._is_enabled != enabled:
            self._is_enabled = enabled
            self._event_bus.publish(
                PluginEnabledChanged(plugin_id=self.node_id,
                                     is_enabled=enabled))

    def get_parameters(self) -> Dict[str, IParameter]:
        return self._parameters

    def get_ports(self, port_type: Optional[str] = None) -> List[Port]:
        return self.descriptor.available_ports

    def get_latency_samples(self) -> int:

        if self.is_enabled and self.descriptor.reports_latency:
            return self.descriptor.latency_samples
        return 0

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self):
        return list(self._parameters.values())

    def get_parameter_values(self) -> Dict[str, Any]:

        return {name: param.value for name, param in self._parameters.items()}

    def set_parameter_value(self, name: str, value: Any):

        if name in self._parameters:
            self._parameters[name].set_value(value)
        else:

            raise KeyError(
                f"Plugin '{self.node_id}' has no parameter named '{name}'")

    def to_state(self) -> PluginState:
        return PluginState(instance_id=self._node_id,
                           unique_plugin_id=self.descriptor.unique_plugin_id,
                           is_enabled=self._is_enabled,
                           parameters={
                               name: param.to_state()
                               for name, param in self._parameters.items()
                           })

    @classmethod
    def from_state(cls, state: PluginState,
                   registry: IPluginRegistry) -> 'Plugin':

        if not registry:
            raise ValueError("Plugin.from_state requires a 'plugin_registry'")

        descriptor = registry.find_by_id(state.unique_plugin_id)
        if not descriptor:
            raise ValueError(
                f"Plugin descriptor '{state.unique_plugin_id}' not found")

        plugin = cls(descriptor=descriptor,
                     event_bus=None,
                     node_id=state.instance_id)
        plugin._is_enabled = state.is_enabled

        # Restore parameter values
        for param_name, param_state in state.parameters.items():
            if param_name in plugin._parameters:
                plugin._parameters[param_name]._base_value = param_state.value
                plugin._parameters[
                    param_name]._automation_lane = param_state.automation_lane

        return plugin

    def to_dict(self) -> Dict[str, Any]:

        return {
            "node_id": self.node_id,
            "descriptor_uri": self.descriptor.uri,
            "is_enabled": self.is_enabled,
            "parameters": self.get_parameter_values()
        }


class PluginCache(IPluginCache):

    def __init__(self,
                 cache_file_path: Path = Path.home() / ".muzaicache.json"):
        self._cache_file = Path(cache_file_path)
        self._cache: Dict[str, CachedPluginInfo] = {}
        print(f"Cache file will be stored at: {self._cache_file}")

    def load(self) -> None:
        if not self._cache_file.exists():
            self._cache = {}
            return
        try:
            with open(self._cache_file, 'r') as f:
                data = json.load(f)
                self._cache = {
                    path:
                    CachedPluginInfo(
                        descriptor=PluginDescriptor(**info['descriptor']),
                        file_mod_time=info['file_mod_time'])
                    for path, info in data.items()
                }
        except (json.JSONDecodeError, KeyError) as e:
            print(
                f"Warning: Could not load cache file, it might be corrupt. Error: {e}"
            )
            self._cache = {}

    def persist(self) -> None:
        try:
            data_to_persist = {
                path: {
                    'descriptor': asdict(info.descriptor),
                    'file_mod_time': info.file_mod_time
                }
                for path, info in self._cache.items()
            }
            with open(self._cache_file, 'w') as f:
                json.dump(data_to_persist, f, indent=4)
        except Exception as e:
            print(f"Error: Could not persist cache. Reason: {e}")

    def get_valid_entry(self,
                        path: Union[Path | str]) -> Optional[CachedPluginInfo]:
        path_str = path if type(path) is str else str(path.resolve())
        cached_info = self._cache.get(path_str)

        if not cached_info:
            return None

        if not path.exists():
            return None

        current_mtime = path.stat().st_mtime
        if cached_info.file_mod_time == current_mtime:
            return cached_info

        return None

    def store_entry(self, path: Path, info: CachedPluginInfo) -> None:
        self._cache[str(path.resolve())] = info

    def get_all_cached_paths(self) -> List[Path]:
        return [Path(p) for p in self._cache.keys()]

    def remove_entry(self, path: Path) -> None:
        path_str = str(path.resolve())
        if path_str in self._cache:
            del self._cache[path_str]
