# file: src/MuzaiCore/core/mixer.py
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .parameter import Parameter
from .plugin import PluginInstance
from ..interfaces import IParameter, IMixerChannel


@dataclass
class Send:
    """Represents a send from one channel to a bus."""
    target_bus_node_id: str
    level: Parameter = field(default_factory=lambda: Parameter(
        "send_level", -100.0))  # Muted by default
    is_post_fader: bool = True  # Sends are post-fader by default


class MixerChannel(IMixerChannel):
    """
    The concrete implementation of a mixer channel strip.
    """

    def __init__(self):
        self.volume = Parameter("volume", -6.0)
        self.pan = Parameter("pan", 0.0)
        self.is_muted = False
        self.is_solo = False

        self._inserts: List[PluginInstance] = []
        self._sends: List[Send] = []

    @property
    def inserts(self) -> List[PluginInstance]:
        return self._inserts

    @property
    def sends(self) -> List[Send]:
        return self._sends

    def get_parameters(self) -> Dict[str, IParameter]:
        params = {"volume": self.volume, "pan": self.pan}
        for i, plugin in enumerate(self._inserts):
            for p_name, p_obj in plugin.get_parameters().items():
                params[f"insert_{i}_{p_name}"] = p_obj
        for i, send in enumerate(self._sends):
            params[f"send_{i}_level"] = send.level
        return params

    def process_block(self, input_buffer, midi_events, context):
        """Processes the signal through the channel strip."""

        # 1. Process Inserts (Plugins)
        processed_buffer = input_buffer
        for plugin in self._inserts:
            processed_buffer = plugin.process_block(processed_buffer,
                                                    midi_events, context)

        # 2. Handle Sends
        # In a real engine, this is where you'd tap the signal to send to buses.
        # Pre-fader sends would tap `processed_buffer` here.
        # We will assume the audio engine handles the actual routing of sends for now.

        # 3. Apply Fader (Volume and Pan)
        # In a real engine, you'd apply gain and panning to `processed_buffer`.
        # volume_linear = 10 ** (self.volume.get_automated_value(context) / 20)
        # processed_buffer = apply_panning(processed_buffer * volume_linear, self.pan.get_automated_value(context))
        final_output = processed_buffer  # Mock implementation

        # Post-fader sends would tap `final_output` here.

        return final_output

    def add_insert(self, plugin: PluginInstance, index: Optional[int] = None):
        if index is None:
            self._inserts.append(plugin)
        else:
            self._inserts.insert(index, plugin)

    def add_send(self, target_bus_node_id: str) -> Send:
        new_send = Send(target_bus_node_id=target_bus_node_id)
        self._sends.append(new_send)
        return new_send
