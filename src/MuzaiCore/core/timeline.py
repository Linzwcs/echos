# file: src/MuzaiCore/core/timeline.py
from typing import List, Tuple, NamedTuple, Optional
import bisect

from ..models.timeline_model import TempoEvent, TimeSignatureEvent
from ..models.event_model import TempoChanged, TimeSignatureChanged  # <-- 新增导入
from ..interfaces.system import ITimeline, IEventBus  # <-- 新增导入


# (TempoMap class remains unchanged)
class TempoMap:

    def __init__(self, initial_tempo: float = 120.0):
        self._tempo = initial_tempo

    def set_constant_tempo(self, bpm: float):
        if bpm <= 0: raise ValueError("BPM must be positive.")
        self._tempo = bpm

    def beats_to_seconds(self, beats: float) -> float:
        return (beats * 60.0) / self._tempo

    def seconds_to_beats(self, seconds: float) -> float:
        return (seconds * self._tempo) / 60.0


class Timeline(ITimeline):
    """
    Timeline 的具体实现，负责处理节拍和秒之间的转换，并支持时间线上的速度和拍号变化。
    """

    def __init__(
        self,
        event_bus: IEventBus,  # <-- 新增
        tempo: float = 120.0,
        time_signature: Tuple[int, int] = (4, 4)):
        self._event_bus = event_bus  # <-- 新增
        self._tempo_events: List[TempoEvent] = [
            TempoEvent(beat=0.0, bpm=tempo)
        ]
        self._time_signature_events: List[TimeSignatureEvent] = [
            TimeSignatureEvent(beat=0.0,
                               numerator=time_signature[0],
                               denominator=time_signature[1])
        ]

    @property
    def tempo(self) -> float:
        return self._tempo_events[0].bpm

    def set_tempo(self, bpm: float):
        self.set_tempo_at_beat(0.0, bpm)

    @property
    def time_signature(self) -> Tuple[int, int]:
        ts = self._time_signature_events[0]
        return (ts.numerator, ts.denominator)

    def set_time_signature(self, numerator: int, denominator: int):
        self.set_time_signature_at_beat(0.0, numerator, denominator)

    def _add_or_update_event(self, event_list: List[NamedTuple],
                             new_event: NamedTuple):
        idx = bisect.bisect_left(event_list, new_event)
        if idx < len(event_list) and event_list[idx].beat == new_event.beat:
            event_list[idx] = new_event
        else:
            event_list.insert(idx, new_event)

    def get_tempo_events(self) -> List[TempoEvent]:
        return list(self._tempo_events)

    def get_time_signature_events(self) -> List[TimeSignatureEvent]:
        return list(self._time_signature_events)

    def _get_active_tempo_at_beat(self, beat: float) -> float:
        idx = bisect.bisect_right(self._tempo_events,
                                  TempoEvent(beat=beat, bpm=0.0))
        return self._tempo_events[idx - 1].bpm

    def _get_active_time_signature_at_beat(self,
                                           beat: float) -> TimeSignatureEvent:
        idx = bisect.bisect_right(
            self._time_signature_events,
            TimeSignatureEvent(beat=beat, numerator=0, denominator=0))
        return self._time_signature_events[idx - 1]

    def beats_to_seconds(self, target_beats: float) -> float:
        if target_beats < 0: return 0.0
        total_seconds = 0.0
        current_beat = 0.0
        relevant_tempo_events = [
            e for e in self._tempo_events if e.beat <= target_beats
        ]
        if not relevant_tempo_events or target_beats > relevant_tempo_events[
                -1].beat:
            relevant_tempo_events.append(
                TempoEvent(beat=target_beats,
                           bpm=self._get_active_tempo_at_beat(target_beats)))

        for i in range(len(relevant_tempo_events) - 1):
            start_event = relevant_tempo_events[i]
            end_event = relevant_tempo_events[i + 1]
            segment_end_beat = min(end_event.beat, target_beats)
            if segment_end_beat > current_beat:
                beats_in_segment = segment_end_beat - current_beat
                tempo_for_segment = start_event.bpm
                total_seconds += (beats_in_segment / tempo_for_segment) * 60.0
            current_beat = segment_end_beat
            if current_beat >= target_beats: break

        if current_beat < target_beats:
            last_tempo = self._get_active_tempo_at_beat(target_beats)
            beats_in_last_segment = target_beats - current_beat
            total_seconds += (beats_in_last_segment / last_tempo) * 60.0
        return total_seconds

    def seconds_to_beats(self, target_seconds: float) -> float:
        if target_seconds < 0: return 0.0
        total_beats = 0.0
        current_seconds = 0.0
        current_beat_pos = 0.0
        tempo_events_with_end = self._tempo_events + [
            TempoEvent(beat=float('inf'), bpm=self._tempo_events[-1].bpm)
        ]

        for i in range(len(tempo_events_with_end) - 1):
            start_event = tempo_events_with_end[i]
            end_event = tempo_events_with_end[i + 1]
            tempo_for_segment = start_event.bpm
            segment_total_beats = end_event.beat - current_beat_pos
            if tempo_for_segment <= 0: continue
            segment_total_seconds = (segment_total_beats /
                                     tempo_for_segment) * 60.0

            if current_seconds + segment_total_seconds >= target_seconds:
                remaining_seconds = target_seconds - current_seconds
                beats_in_remaining_seconds = (remaining_seconds *
                                              tempo_for_segment) / 60.0
                total_beats += beats_in_remaining_seconds
                return total_beats
            else:
                total_beats += segment_total_beats
                current_seconds += segment_total_seconds
                current_beat_pos = end_event.beat
        return total_beats

    def samples_to_beats(self, samples: int, sample_rate: int) -> float:
        if sample_rate <= 0: raise ValueError("Sample rate must be positive.")
        seconds = samples / sample_rate
        return self.seconds_to_beats(seconds)

    def beats_to_samples(self, beats: float, sample_rate: int) -> int:
        if sample_rate <= 0: raise ValueError("Sample rate must be positive.")
        seconds = self.beats_to_seconds(beats)
        samples = seconds * sample_rate
        return round(samples)

    # subscribe 方法被移除

    def set_tempo_at_beat(self, beat: float, bpm: float):
        if beat < 0: return
        new_tempo_event = TempoEvent(beat=beat, bpm=bpm)
        self._add_or_update_event(self._tempo_events, new_tempo_event)

        # 发布事件
        self._event_bus.publish(TempoChanged(beat=beat, new_bpm=bpm))

    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        if beat < 0: return
        new_ts_event = TimeSignatureEvent(beat=beat,
                                          numerator=numerator,
                                          denominator=denominator)
        self._add_or_update_event(self._time_signature_events, new_ts_event)

        # 发布事件
        self._event_bus.publish(
            TimeSignatureChanged(beat=beat,
                                 numerator=numerator,
                                 denominator=denominator))
