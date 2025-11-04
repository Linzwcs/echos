from dataclasses import dataclass, field
from enum import Flag, auto, Enum
from typing import List, Dict, Union
from .clip_model import AnyClip
from .parameter_model import ParameterState


@dataclass
class PluginState:

    instance_id: str
    unique_plugin_id: str
    is_enabled: bool = True
    parameters: Dict[str, ParameterState] = field(default_factory=dict)


@dataclass
class TrackState:

    node_id: str
    name: str
    track_type: str
    clips: List[AnyClip] = field(default_factory=list)
    plugins: List[PluginState] = field(default_factory=list)
    volume: ParameterState = field(
        default_factory=lambda: ParameterState("volume", -6.0))
    pan: ParameterState = field(
        default_factory=lambda: ParameterState("pan", 0.0))
    is_muted: bool = False
    is_solo: bool = False


class VCAControlMode(Flag):
    NONE = 0
    VOLUME = auto()
    PAN = auto()
    MUTE = auto()
    ALL = VOLUME | PAN | MUTE

    def controls_volume(self) -> bool:
        return bool(self & VCAControlMode.VOLUME)

    def controls_pan(self) -> bool:
        return bool(self & VCAControlMode.PAN)

    def controls_mute(self) -> bool:
        return bool(self & VCAControlMode.MUTE)


class TrackRecordMode(Enum):
    NORMAL = "normal"
    OVERDUB = "overdub"
    REPLACE = "replace"
    LOOP = "loop"


# A NodeState is a union of all possible node types
NodeState = Union[TrackState, PluginState]
