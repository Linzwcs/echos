# file: src/MuzaiCore/models/plugin_model.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum
from .routing_model import Port


@dataclass
class CachedPluginInfo:
    metadata: Dict[str, Any]
    file_mod_time: float
    file_size: int


class PluginCategory(Enum):
    INSTRUMENT = "instrument"
    EFFECT = "effect"
    MIDI_EFFECT = "midi_effect"


@dataclass(frozen=True)
class PluginDescriptor:

    unique_plugin_id: str
    name: str
    vendor: str
    meta: str
    category: PluginCategory
    reports_latency: bool = True
    latency_samples: int = 0
    available_ports: List[Port] = field(default_factory=list)

    default_parameters: Dict[str, Any] = field(default_factory=dict)
