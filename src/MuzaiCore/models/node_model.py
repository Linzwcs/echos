# file: src/MuzaiCore/models/node_model.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union
from .clip_model import AnyClip
from .parameter_model import ParameterState


@dataclass
class PluginState:
    """Serializable state for a plugin instance."""
    instance_id: str
    unique_plugin_id: str  # Refers to the plugin type, e.g., "com.native-instruments.massive-x"
    is_enabled: bool = True
    parameters: Dict[str, ParameterState] = field(default_factory=dict)


@dataclass
class TrackState:
    """Serializable state for a track instance."""
    node_id: str
    name: str
    track_type: str  # e.g., 'instrument', 'audio'
    clips: List[AnyClip] = field(default_factory=list)
    plugins: List[PluginState] = field(
        default_factory=list)  # Ordered list of plugin instances
    volume: ParameterState = field(
        default_factory=lambda: ParameterState("volume", -6.0))
    pan: ParameterState = field(
        default_factory=lambda: ParameterState("pan", 0.0))
    is_muted: bool = False
    is_solo: bool = False


# A NodeState is a union of all possible node types
NodeState = Union[TrackState, PluginState]
