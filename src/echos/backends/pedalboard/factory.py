from .engine import PedalboardEngine
from .plugin_ins_manager import PedalboardPluginInstanceManager
from ...core.plugin import PluginRegistry
from ...interfaces.system.ifactory import INodeFactory
from ...interfaces.system import IPlugin, ITrack, IEngine
from ...models import PluginDescriptor
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import Plugin
from ...interfaces.system.ifactory import IEngineFactory


class PedalboardEngineFactory(IEngineFactory):

    def create_engine(
        self,
        plugin_registry: PluginRegistry,
        sample_rate: int = 48000,
        block_size: int = 512,
        output_channels: int = 2,
        device_id=None,
    ) -> IEngine:
        plugin_ins_manager = PedalboardPluginInstanceManager(
            registry=plugin_registry)
        return PedalboardEngine(
            sample_rate=sample_rate,
            block_size=block_size,
            output_channels=output_channels,
            plugin_ins_manager=plugin_ins_manager,
            device_id=device_id,
        )


class PedalboardNodeFactory(INodeFactory):

    def create_instrument_track(self, name: str, track_id=None) -> ITrack:
        return InstrumentTrack(name=name, node_id=track_id)

    def create_audio_track(self, name: str, track_id=None) -> ITrack:
        return AudioTrack(name=name, node_id=track_id)

    def create_bus_track(self, name: str, track_id=None) -> ITrack:
        return BusTrack(name=name, node_id=track_id)

    def create_vca_track(self, name: str, track_id=None) -> ITrack:
        return VCATrack(name=name, node_id=track_id)

    def create_plugin_instance(self, descriptor: PluginDescriptor,
                               plugin_instance_id: str) -> IPlugin:
        return Plugin(descriptor=descriptor,
                      event_bus=None,
                      plugin_instance_id=plugin_instance_id)
