from abc import ABC, abstractmethod
from typing import Dict, List
from .ilifecycle import ILifecycleAware
from .iserializable import ISerializable
from .iparameter import IParameter
from .imixer import IMixerChannel
from ...models import AnyClip


class INode(
        ILifecycleAware,
        ISerializable,
        ABC,
):

    @property
    @abstractmethod
    def node_id(self) -> str:
        pass

    @property
    @abstractmethod
    def node_type(self) -> str:
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
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

    @property
    @abstractmethod
    def mixer_channel(self) -> IMixerChannel:
        pass

    @abstractmethod
    def add_clip(self, clip: AnyClip):
        pass
