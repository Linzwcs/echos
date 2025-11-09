from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum
from .router_model import Port


class PluginCategory(Enum):
    INSTRUMENT = "instrument"
    EFFECT = "effect"


@dataclass(frozen=True)
class PluginDescriptor:

    unique_plugin_id: str
    name: str
    vendor: str
    path: str
    is_instrument: bool
    plugin_format: str
    reports_latency: bool = True
    latency_samples: int = 0
    available_ports: List[Port] = field(default_factory=list)
    default_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedPluginInfo:
    descriptor: PluginDescriptor
    file_mod_time: float
