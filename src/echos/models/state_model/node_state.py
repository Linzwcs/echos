from dataclasses import dataclass, field
from typing import List
from .base_state import BaseState
from .mixer_state import MixerState
from ..clip_model import AnyClip


@dataclass(frozen=True)
class NodeState(BaseState):
    node_id: str
    node_type: str


@dataclass(frozen=True)
class TrackState(NodeState):

    name: str
    track_type: str
    mixer_state: MixerState
    clips: List[AnyClip] = field(default_factory=list)


@dataclass(frozen=True)
class VCATrackState(NodeState):
    name: str
    controlled_track_ids: List[str] = field(default_factory=list)
