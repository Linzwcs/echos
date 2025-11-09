from dataclasses import dataclass, field
from typing import List
from .parameter_state import ParameterState
from .plugin_state import PluginState
from .base_state import BaseState


@dataclass(frozen=True)
class SendState(BaseState):

    send_id: str
    target_bus_node_id: str
    level: ParameterState
    is_post_fader: bool
    is_enabled: bool


@dataclass(frozen=True)
class MixerState(BaseState):

    channel_id: str
    volume: ParameterState
    pan: ParameterState
    input_gain: ParameterState
    is_muted: bool
    is_solo: bool
    inserts: List[PluginState] = field(default_factory=list)
    sends: List[SendState] = field(default_factory=list)
