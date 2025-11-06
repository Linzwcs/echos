from abc import ABC, abstractmethod
from .inode import IPlugin, ITrack
from .iengine import IEngine
from .iregistry import IPluginRegistry
from ...models import PluginDescriptor


class IEngineFactory(ABC):

    @abstractmethod
    def create_engine(
        self,
        plugin_registry: IPluginRegistry,
        sample_rate: int = 48000,
        block_size: int = 512,
        output_channels: int = 2,
        device_id=None,
    ) -> IEngine:
        pass


class INodeFactory(ABC):

    @abstractmethod
    def create_instrument_track(self, name: str, track_id=None) -> ITrack:
        pass

    @abstractmethod
    def create_audio_track(self, name: str, track_id=None) -> ITrack:
        pass

    @abstractmethod
    def create_bus_track(self, name: str, track_id=None) -> ITrack:
        pass

    @abstractmethod
    def create_vca_track(self, name: str, track_id=None) -> ITrack:
        pass
