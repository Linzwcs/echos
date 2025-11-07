from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .ilifecycle import ILifecycleAware
from .iparameter import IParameter
from ...models import Send, AnyClip, PluginDescriptor


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


class IMixerChannel(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def channel_id(self) -> str:
        pass

    @property
    @abstractmethod
    def volume(self) -> IParameter:
        pass

    @property
    @abstractmethod
    def pan(self) -> IParameter:
        pass

    @property
    @abstractmethod
    def inserts(self) -> List[IPlugin]:
        pass

    @property
    @abstractmethod
    def sends(self) -> List[Send]:
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
        pass

    @abstractmethod
    def add_insert(self, plugin: IPlugin, index: Optional[int] = None):
        pass

    @abstractmethod
    def remove_insert(self, plugin_instance_id: str) -> bool:
        pass

    @abstractmethod
    def move_insert(self, plugin_instance_id: str, new_index: int) -> bool:
        pass

    @abstractmethod
    def add_send(
        self,
        target_bus_node_id: str,
        is_post_fader: bool = True,
    ) -> Send:
        pass

    @abstractmethod
    def remove_send(self, send_id: str) -> bool:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
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

    @property
    @abstractmethod
    def mixer_channel(self) -> IMixerChannel:
        pass

    @abstractmethod
    def add_clip(self, clip: AnyClip):
        pass
