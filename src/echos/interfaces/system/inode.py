from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .ilifecycle import ILifecycleAware
from .ievent_bus import IEventBus
from ...models import AnyClip, Port


class INode(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def node_id(self) -> str:
        pass

    @property
    @abstractmethod
    def node_type(self) -> str:
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class ITrack(INode):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @name.setter
    @abstractmethod
    def name(self, value: str):
        pass

    @property
    @abstractmethod
    def clips(self) -> List[AnyClip]:
        pass

    @abstractmethod
    def add_clip(self, clip: AnyClip):
        pass


class IPlugin(INode):

    @property
    @abstractmethod
    def descriptor(self) -> 'PluginDescriptor':
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        pass

    @abstractmethod
    def get_parameter_values(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_parameter_value(self, name: str, value: Any):
        pass
