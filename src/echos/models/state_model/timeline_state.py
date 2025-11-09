from dataclasses import dataclass
from .base_state import BaseState
from ..timeline_model import Tempo, TimeSignature


@dataclass(frozen=True)
class TimelineState(BaseState):
    tempos: list[Tempo]
    time_signatures: list[TimeSignature]
