from .engine import PedalboardEngine
from ...interfaces.system.ifactory import INodeFactory
from ...interfaces.system import IPlugin, ITrack, IEngine
from ...models import PluginDescriptor
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import Plugin
from ...interfaces.system.ifactory import IEngineFactory


class PedalboardEngineFactory(IEngineFactory):

    def create_engine(
        self,
        sample_rate: int = 48000,
        block_size: int = 512,
    ) -> IEngine:
        return PedalboardEngine(
            sample_rate=sample_rate,
            block_size=block_size,
        )


class PedalboardNodeFactory(INodeFactory):

    def create_instrument_track(self, name: str) -> ITrack:

        return InstrumentTrack(name=name)

    def create_audio_track(self, name: str) -> ITrack:

        return AudioTrack(name=name)

    def create_bus_track(self, name: str) -> ITrack:

        return BusTrack(name=name)

    def create_vca_track(self, name: str) -> ITrack:

        return VCATrack(name=name)

    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:

        return Plugin(
            descriptor=descriptor,
            event_bus=None,  # 将在 mount 时设置
        )
