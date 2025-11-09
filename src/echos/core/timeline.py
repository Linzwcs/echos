from typing import List, Tuple
import bisect
from .event_bus import EventBus
from ..interfaces.system import IDomainTimeline
from ..models.timeline_model import Tempo, TimeSignature, TimelineState


class Timeline(IDomainTimeline):

    def __init__(self,
                 tempos: list[Tempo] = None,
                 time_signatures: list[TimeSignature] = None):

        super().__init__()
        self._tempos: List[Tempo] = tempos or [Tempo(beat=0.0, bpm=120.0)]
        self._time_signatures: List[TimeSignature] = time_signatures or [
            TimeSignature(beat=0.0, numerator=4, denominator=4)
        ]

    @property
    def timeline_state(self):
        return TimelineState(tempos=self.tempos[:],
                             time_signatures=self.time_signatures[:])

    @property
    def tempos(self) -> List[Tempo]:
        return list(self._tempos)

    @property
    def time_signatures(self) -> List[TimeSignature]:
        return list(self._time_signatures)

    def set_state(self, new_state: TimelineState) -> TimelineState:
        old_state = self.timeline_state
        self._validate_state(new_state)
        self._tempos = new_state.tempos
        self._time_signatures = new_state.time_signatures
        self._sync_timeline_state()
        return old_state

    def set_tempo(self, beat: float, bpm: float):
        if beat < 0 or bpm <= 0:
            return

        new_state = self.timeline_state

        new_event = Tempo(beat=beat, bpm=bpm)
        idx = bisect.bisect_left(new_state.tempos, beat, key=lambda t: t.beat)

        if idx < len(new_state.tempos) and new_state.tempos[idx].beat == beat:
            new_state.tempos[idx] = new_event
        else:
            new_state.tempos.insert(idx, new_event)

        self.set_state(new_state)

    def set_time_signature(self, beat: float, numerator: int,
                           denominator: int):

        if beat < 0 or numerator <= 0 or denominator <= 0:
            return

        new_state = self.timeline_state
        new_event = TimeSignature(beat=beat,
                                  numerator=numerator,
                                  denominator=denominator)
        idx = bisect.bisect_left(new_state.time_signatures,
                                 beat,
                                 key=lambda t: t.beat)

        if idx < len(new_state.time_signatures
                     ) and new_state.time_signatures[idx].beat == beat:
            new_state.time_signatures[idx] = new_event
        else:
            new_state.time_signatures.insert(idx, new_event)

        self.set_state(new_state)

    def remove_tempo(self, beat: float):

        if beat <= 0:
            return
        new_state = self.timeline_state
        original_len = len(new_state.tempos)
        new_state.tempos = [t for t in new_state.tempos if t.beat != beat]

        if len(new_state.tempos) < original_len:
            self.set_state(new_state)

    def remove_time_signature(self, beat: float):

        if beat <= 0:
            return

        new_state = self.timeline_state
        original_len = len(new_state.time_signatures)
        new_state.time_signatures = [
            ts for ts in new_state.time_signatures if ts.beat != beat
        ]
        if len(new_state.time_signatures) < original_len:
            self.set_state(new_state)

    def beats_to_seconds(self, target_beats: float) -> float:

        if target_beats < 0:
            return 0.0

        total_seconds = 0.0
        current_beat = 0.0

        relevant_events = [e for e in self._tempos if e.beat <= target_beats]
        if not relevant_events or target_beats > relevant_events[-1].beat:
            relevant_events.append(
                Tempo(beat=target_beats,
                      bpm=self.get_tempo_at_beat(target_beats)))

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

    def get_tempo_at_beat(self, beat: float) -> float:

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

    def to_state(self):
        return self.timeline_state

    @classmethod
    def from_state(cls, state: TimelineState, **kwargs) -> 'Timeline':
        return Timeline(tempos=state.tempos,
                        time_signatures=state.time_signatures)

    def _sync_timeline_state(self):
        if self.is_mounted:
            from ..models.event_model import TimelineStateChanged
            event = TimelineStateChanged(timeline_state=self.timeline_state)
            self._event_bus.publish(event)

    def _validate_state(self, state: TimelineState):
        if not state.tempos or state.tempos[0].beat != 0.0:
            raise ValueError(
                "Tempos list must not be empty and must start at beat 0.0.")
        if any(state.tempos[i].beat > state.tempos[i + 1].beat
               for i in range(len(state.tempos) - 1)):
            raise ValueError("Tempos list must be sorted by beat.")

        if not state.time_signatures or state.time_signatures[0].beat != 0.0:
            raise ValueError(
                "Time signatures list must not be empty and must start at beat 0.0."
            )
        if any(state.time_signatures[i].beat > state.time_signatures[i +
                                                                     1].beat
               for i in range(len(state.time_signatures) - 1)):
            raise ValueError("Time signatures list must be sorted by beat.")

    def _on_mount(self, event_bus: EventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self):
        return []
