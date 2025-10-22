# file: src/MuzaiCore/implementations/mock/plugin_registry.py
from typing import List, Optional, Dict

from ...interfaces import IPluginRegistry
from ...models.plugin_model import PluginDescriptor, PluginCategory
from ...subsystems.routing.routing_types import Port, PortType, PortDirection


class MockPluginRegistry(IPluginRegistry):
    """A mock implementation of a plugin registry with pre-defined virtual plugins."""

    def __init__(self):
        self._plugins: Dict[str, PluginDescriptor] = {}

    def scan_for_plugins(self):
        print("MockPluginRegistry: Scanning for virtual plugins...")
        self._plugins.clear()

        # A virtual Instrument plugin
        synth_ports = [
            Port("self", "midi_in", PortType.MIDI, PortDirection.INPUT),
            Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT, 2)
        ]
        synth_params = {
            "attack": 0.01,
            "decay": 0.2,
            "sustain": 0.8,
            "release": 0.1,
            "cutoff": 12000.0
        }
        synth_descriptor = PluginDescriptor(
            unique_plugin_id="muzaicore.mock.basic_synth",
            name="Basic Synth",
            vendor="MuzaiCore",
            category=PluginCategory.INSTRUMENT,
            available_ports=synth_ports,
            default_parameters=synth_params)
        self._plugins[synth_descriptor.unique_plugin_id] = synth_descriptor

        # A virtual Effect plugin
        reverb_ports = [
            Port("self", "audio_in", PortType.AUDIO, PortDirection.INPUT, 2),
            Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT, 2)
        ]
        reverb_params = {"size": 0.7, "damping": 0.5, "mix": 0.3}
        reverb_descriptor = PluginDescriptor(
            unique_plugin_id="muzaicore.mock.simple_reverb",
            name="Simple Reverb",
            vendor="MuzaiCore",
            category=PluginCategory.EFFECT,
            available_ports=reverb_ports,
            default_parameters=reverb_params)
        self._plugins[reverb_descriptor.unique_plugin_id] = reverb_descriptor

        print(f"MockPluginRegistry: Found {len(self._plugins)} plugins.")

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        return self._plugins.get(unique_plugin_id)

    def list_plugins(self) -> List[PluginDescriptor]:
        return list(self._plugins.values())
