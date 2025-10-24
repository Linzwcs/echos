# file: src/MuzaiCore/models/plugin_model.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum

from .routing_model import Port


class PluginCategory(Enum):
    INSTRUMENT = "instrument"
    EFFECT = "effect"
    MIDI_EFFECT = "midi_effect"


@dataclass(frozen=True)
class PluginDescriptor:
    """
    Static, read-only information about a discoverable plugin.
    This acts as a blueprint for creating PluginInstance objects.
    """
    unique_plugin_id: str  # e.g., "native_instruments.massive_x.vst3"
    name: str
    vendor: str
    category: PluginCategory
    reports_latency: bool = True
    latency_samples: int = 0  # +++ NEW: The latency this plugin reports in samples.
    # Pre-defined list of available audio/MIDI ports
    available_ports: List[Port] = field(default_factory=list)

    # Default values for all parameters
    default_parameters: Dict[str, Any] = field(default_factory=dict)
