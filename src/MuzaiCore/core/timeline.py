from typing import List, Tuple
import bisect
from ..interfaces.system import ITimeline
from ..models.timeline_model import Tempo, TimeSignature


class Timeline(ITimeline):

    def __init__(self,
                 tempo: float = 120.0,
                 time_signature: Tuple[int, int] = (4, 4)):
        super().__init__()
        self._tempos: List[Tempo] = [Tempo(beat=0.0, bpm=tempo)]
        self._time_signatures: List[TimeSignature] = [
            TimeSignature(beat=0.0,
                          numerator=time_signature[0],
                          denominator=time_signature[1])
        ]

    @property
    def tempos(self) -> List[Tempo]:
        return list(self._tempos)

    @property
    def time_signatures(self) -> List[TimeSignature]:
        return list(self._time_signatures)

    def set_tempos(self, tempos: list[Tempo]):
        self._tempos = tempos

    def set_time_signatures(self, time_signatures: list[TimeSignature]):
        self._time_signatures = time_signatures

    @property
    def time_signature(self) -> Tuple[int, int]:
        ts = self._time_signatures[0]
        return (ts.numerator, ts.denominator)

    def set_tempo_at_beat(self, beat: float, bpm: float):

        if beat < 0:
            return

        new_event = Tempo(beat=beat, bpm=bpm)
        idx = bisect.bisect_left(self._tempos, new_event)

        if idx < len(self._tempos) and self._tempos[idx].beat == beat:
            self._tempos[idx] = new_event
        else:
            self._tempos.insert(idx, new_event)

        self._sync_tempos()

    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):

        if beat < 0:
            return

        new_event = TimeSignature(beat=beat,
                                  numerator=numerator,
                                  denominator=denominator)
        idx = bisect.bisect_left(self._time_signatures, new_event)

        if idx < len(self._time_signatures
                     ) and self._time_signatures[idx].beat == beat:
            self._time_signatures[idx] = new_event
        else:
            self._time_signatures.insert(idx, new_event)

        self._sync_time_signatures()

    def beats_to_seconds(self, target_beats: float) -> float:

        if target_beats < 0:
            return 0.0

        total_seconds = 0.0
        current_beat = 0.0

        relevant_events = [e for e in self._tempos if e.beat <= target_beats]
        if not relevant_events or target_beats > relevant_events[-1].beat:
            relevant_events.append(
                Tempo(beat=target_beats,
                      bpm=self._get_tempo_at_beat(target_beats)))

        for i in range(len(relevant_events) - 1):
            start_event = relevant_events[i]
            end_event = relevant_events[i + 1]
            segment_end = min(end_event.beat, target_beats)

            if segment_end > current_beat:
                beats_in_segment = segment_end - current_beat
                total_seconds += (beats_in_segment / start_event.bpm) * 60.0

            current_beat = segment_end
            if current_beat >= target_beats:
                break

        return total_seconds

    def seconds_to_beats(self, target_seconds: float) -> float:

        if target_seconds < 0:
            return 0.0

        total_beats = 0.0
        current_seconds = 0.0
        current_beat = 0.0

        events_with_end = self._tempos + [
            Tempo(beat=float('inf'), bpm=self._tempos[-1].bpm)
        ]

        for i in range(len(events_with_end) - 1):
            start_event = events_with_end[i]
            end_event = events_with_end[i + 1]
            tempo = start_event.bpm

            if tempo <= 0:
                continue

            segment_beats = end_event.beat - current_beat
            segment_seconds = (segment_beats / tempo) * 60.0

            if current_seconds + segment_seconds >= target_seconds:
                remaining_seconds = target_seconds - current_seconds
                beats_in_remaining = (remaining_seconds * tempo) / 60.0
                total_beats += beats_in_remaining
                return total_beats
            else:
                total_beats += segment_beats
                current_seconds += segment_seconds
                current_beat = end_event.beat

        return total_beats

    def samples_to_beats(self, samples: int, sample_rate: int) -> float:

        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        seconds = samples / sample_rate
        return self.seconds_to_beats(seconds)

    def beats_to_samples(self, beats: float, sample_rate: int) -> int:

        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        seconds = self.beats_to_seconds(beats)
        return round(seconds * sample_rate)

    def _get_tempo_at_beat(self, beat: float) -> float:

        idx = bisect.bisect_right(self._tempos, Tempo(beat=beat, bpm=0.0))
        return self._tempos[idx - 1].bpm

    def _sync_tempos(self):

        if self.is_mounted:
            from ..models.event_model import TempoChanged
            event = TempoChanged(tempos=self._tempos)
            self._event_bus.publish(event)

    def _sync_time_signatures(self):

        if self.is_mounted:
            from ..models.event_model import TimeSignatureChanged
            event = TimeSignatureChanged(time_signatures=self._time_signatures)
            self._event_bus.publish(event)
