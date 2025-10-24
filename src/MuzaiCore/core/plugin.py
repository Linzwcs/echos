# file: src/MuzaiCore/core/plugin.py
import uuid
from typing import Dict, List, Optional
from abc import ABC

from .parameter import Parameter
from ..interfaces.IPlugin import IPlugin
from ..interfaces.IParameter import IParameter

from ..models import Port, PortType
from ..models.plugin_model import PluginDescriptor
from ..models.engine_model import TransportContext, MIDIEvent


# This base class is now almost identical to the RealDAW design
class PluginInstance(IPlugin, ABC):
    """Represents an active instance of a plugin within a project. (Abstract Base)"""

    def __init__(self,
                 descriptor: PluginDescriptor,
                 instance_id: Optional[str] = None):
        self._node_id = instance_id or str(uuid.uuid4())
        self.descriptor = descriptor
        self.is_enabled = True
        self._parameters = self._create_parameters_from_descriptor()

    @property
    def node_id(self) -> str:
        return self._node_id

    def get_parameters(self) -> Dict[str, IParameter]:
        return self._parameters

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        # Update owner_node_id for ports from descriptor's template
        ports = [
            Port(self.node_id, p.port_id, p.port_type, p.direction,
                 p.channel_count) for p in self.descriptor.available_ports
        ]
        if port_type:
            return [p for p in ports if p.port_type == port_type]
        return ports

    def _create_parameters_from_descriptor(self) -> Dict[str, Parameter]:
        params = {}
        for name, default_value in self.descriptor.default_parameters.items():
            params[name] = Parameter(name, default_value)
        return params

    def process_block(self, input_buffer, midi_events, context):
        # The generic process_block. Subclasses will provide specific logic.
        if not self.is_enabled:
            return input_buffer
        return self._process_internal(input_buffer, midi_events, context)

    def _process_internal(self, input_buffer, midi_events, context):
        raise NotImplementedError

    # +++ FIX: Implementing the abstract method from IPlugin +++
    def get_latency_samples(self) -> int:
        """
        Returns the processing latency introduced by the plugin in samples.
        This mock implementation reads the value from its descriptor.
        """
        if self.is_enabled and self.descriptor.reports_latency:
            return self.descriptor.latency_samples
        return 0


class InstrumentPluginInstance(PluginInstance):
    """A mock instrument. It "generates sound" (logs) from MIDI."""

    def _process_internal(self, input_buffer, midi_events, context):
        if midi_events:
            print(
                f"      -> Instrument '{self.descriptor.name}' ({self.node_id[:4]}) received {len(midi_events)} MIDI events."
            )
        # In mock, it doesn't return an audio buffer, just a signal that it was processed.
        return "processed_audio_signal"


class EffectPluginInstance(PluginInstance):
    """A mock effect. It "processes sound" (logs)."""

    def _process_internal(self, input_buffer, midi_events, context):
        if input_buffer:
            print(
                f"      -> Effect '{self.descriptor.name}' ({self.node_id[:4]}) is processing a signal."
            )
        else:
            print(
                f"      -> Effect '{self.descriptor.name}' ({self.node_id[:4]}) received no input signal."
            )
        return input_buffer
