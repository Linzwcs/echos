# file: src/MuzaiCore/backends/dawdreamer/factory.py
"""
Node Factory for the DawDreamer backend. It creates the backend-agnostic
domain model objects from `MuzaiCore.core`.
"""
from ...interfaces.system import INodeFactory, IPlugin, ITrack
from ...models import PluginDescriptor
from ...core.track import InstrumentTrack, AudioTrack, BusTrack
from ...core.plugin import Plugin


class DawDreamerNodeFactory(INodeFactory):
    """
    Creates domain objects. It does NOT interact with the DawDreamer engine
    directly. That is the job of the SyncController.
    """

    def create_instrument_track(self, name: str) -> ITrack:
        return InstrumentTrack(name=name)

    def create_audio_track(self, name: str) -> ITrack:
        return AudioTrack(name=name)

    def create_bus_track(self, name: str) -> ITrack:
        return BusTrack(name=name)

    def create_vca_track(self, name: str) -> ITrack:
        return BusTrack(name=name)

    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:
        """
        Creates a generic PluginInstance domain object. This object holds the
        state that will be synced to the actual DawDreamer processor.
        """
        return Plugin(descriptor=descriptor)
