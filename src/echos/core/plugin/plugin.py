import uuid
from typing import Any, Dict, List, Optional
from echos.interfaces.system import IPluginRegistry
from ..parameter import Parameter
from ...interfaces.system import IPlugin, IParameter, IEventBus
from ...models import PluginDescriptor, Port, PluginDescriptor
from ...models.event_model import PluginEnabledChanged
from ...models.state_model import PluginState


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

        for param_name, param_state in state.parameters.items():
            if param_name in plugin._parameters:
                plugin._parameters[param_name]._base_value = param_state.value
                plugin._parameters[
                    param_name]._automation_lane = param_state.automation_lane

        return plugin
