from abc import ABC, abstractmethod
from .inode import IPlugin, ITrack
from .iengine import IEngine
from ...models import PluginDescriptor


class IEngineFactory(ABC):

    @abstractmethod
    def create_engine(
        self,
        sample_rate: int,
        block_size: int,
    ) -> IEngine:
        pass


class INodeFactory(ABC):

    @abstractmethod
    def create_instrument_track(self, name: str) -> ITrack:
        pass

    @abstractmethod
    def create_audio_track(self, name: str) -> ITrack:
        pass

    @abstractmethod
    def create_bus_track(self, name: str) -> ITrack:
        pass

    @abstractmethod
    def create_vca_track(self, name: str) -> ITrack:
        pass

    @abstractmethod
    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:
        pass
