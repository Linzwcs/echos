from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


@dataclass
class PluginScanResult:
    success: bool
    plugin_info: Optional[Dict] = None
    error: Optional[str] = None


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
    #available_ports: List[Port] = field(default_factory=list)
    default_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedPluginInfo:
    descriptor: PluginDescriptor
    file_mod_time: float
