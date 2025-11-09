from abc import ABC, abstractmethod
from typing import Any, Dict
from .ilifecycle import ILifecycleAware
from .iparameter import IParameter
from .iserializable import ISerializable
from ...models import PluginDescriptor


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

    @abstractmethod
    def to_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass
