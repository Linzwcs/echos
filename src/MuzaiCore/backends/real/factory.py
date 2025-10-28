# file: src/MuzaiCore/backends/real/factory.py
from ...interfaces.system import INodeFactory, IPlugin, ITrack
from ...models import PluginDescriptor
from ...core.track import InstrumentTrack, AudioTrack
from .plugin import RealPlugin


class RealNodeFactory(INodeFactory):

    def create_instrument_track(self, name: str) -> ITrack:
        return InstrumentTrack(name=name)

    def create_audio_track(self, name: str) -> ITrack:
        return AudioTrack(name=name)

    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:
        """
        Factory method for the 'real' backend.
        It creates a RealPluginAdapter which contains Python DSP logic.
        """
        return RealPlugin(descriptor=descriptor)
