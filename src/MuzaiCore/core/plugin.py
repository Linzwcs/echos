# file: src/MuzaiCore/core/plugin.py
from typing import Any, Dict, List, Optional
import uuid
import numpy as np

from ..interfaces.system import IPlugin, IParameter, IEventBus
from ..models import PluginDescriptor, Port
from ..models.event_model import PluginEnabledChanged
from .parameter import Parameter


class Plugin(IPlugin):
    """
    The backend-agnostic domain model for a plugin instance.
    """

    def __init__(
            self,
            descriptor: PluginDescriptor,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        super().__init__()
        self._node_id = node_id or f"plugin_{uuid.uuid4()}"
        self._descriptor = descriptor
        self._event_bus = event_bus  # <-- 新增
        self._is_enabled = True
        self._parameters: Dict[str, IParameter] = {
            name:
            Parameter(
                owner_node_id=self._node_id,
                name=name,
                default_value=default_value,
            )
            for name, default_value in descriptor.default_parameters.items()
        }

    @property
    def descriptor(self):
        return self._descriptor

    @property
    def node_id(self) -> str:
        return self._node_id

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
        """Returns the static latency reported by the plugin descriptor."""
        if self.is_enabled and self.descriptor.reports_latency:
            return self.descriptor.latency_samples
        return 0

    def _get_children(self):
        return list(self._parameters.values())

    def get_parameter_values(self) -> Dict[str, Any]:
        """
        [实现] 以字典形式返回所有参数的当前值。
        """
        return {name: param.value for name, param in self._parameters.items()}

    def set_parameter_value(self, name: str, value: Any):
        """
        [实现] 设置指定名称的参数的值。
        """
        if name in self._parameters:
            self._parameters[name].set_value(value)
        else:
            # 或者可以抛出一个更具体的异常类型
            raise KeyError(
                f"Plugin '{self.node_id}' has no parameter named '{name}'")

    def to_dict(self) -> Dict[str, Any]:
        """
        [实现] 将插件的当前状态序列化为一个字典。
        """
        return {
            "node_id": self.node_id,
            "descriptor_uri": self.descriptor.uri,  # 假设 descriptor 有 'uri' 属性
            "is_enabled": self.is_enabled,
            "parameters": self.get_parameter_values()
        }
