from typing import List, Tuple
import bisect
from ...interfaces.system import IEngineTimeline
from ...models import Tempo, TimeSignature


class RealTimeTimeline(IEngineTimeline):

    def __init__(self):
        self._tempos: List[Tempo] = []
        self._time_signatures: List[TimeSignature] = []

    def update_tempos(self, events: Tuple[Tempo]):
        self._tempos = list(events)

    def update_time_signatures(self, events: Tuple[TimeSignature]):
        self._time_signature_events = list(events)

    def get_tempo_at_beat(self, beat: float) -> float:
        if not self._tempos:
            return 120.0

        idx = bisect.bisect_right(self._tempos, Tempo(beat=beat, bpm=None))
        if idx == 0:
            return self._tempos[0].bpm

        return self._tempos[idx - 1].bpm
