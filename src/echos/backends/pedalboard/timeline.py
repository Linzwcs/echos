from typing import List, Tuple
import bisect
import math
from ...interfaces.system import IEngineTimeline, IDomainTimeline
from ...models import Tempo, TimeSignature
from ...models.state_model import TimelineState


class RealTimeTimeline(IEngineTimeline):

    def __init__(self):
        self._tempos: List[Tempo] = [Tempo(beat=0, bpm=120)]
        self._time_signatures: List[TimeSignature] = [
            TimeSignature(beat=0, numerator=4, denominator=4)
        ]

    @property
    def tempos(self) -> List[Tempo]:
        return list(self._tempos)

    @property
    def time_signatures(self) -> List[TimeSignature]:
        return list(self._time_signatures)

    def set_state(self, new_state: TimelineState) -> TimelineState:
        self._tempos = new_state.tempos
        self._time_signatures = new_state.time_signatures

    def get_tempo_at_beat(self, beat: float) -> Tempo:

        idx = bisect.bisect_right(self._tempos, beat, key=lambda t: t.beat)
        return self._tempos[idx - 1]

    def get_time_signature_at_beat(self, beat: float) -> TimeSignature:
        if not self._time_signatures:
            return TimeSignature(beat=0.0, numerator=4, denominator=4)

        idx = bisect.bisect_right(self._time_signatures,
                                  beat,
                                  key=lambda t: t.beat)
        if idx == 0:
            return self._time_signatures[0]

        return self._time_signatures[idx - 1]
