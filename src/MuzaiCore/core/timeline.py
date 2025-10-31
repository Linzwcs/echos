# file: src/MuzaiCore/core/timeline.py
from typing import List, Tuple, NamedTuple, Optional
import bisect

from ..models.timeline_model import TempoEvent, TimeSignatureEvent
from ..models.event_model import TempoChanged, TimeSignatureChanged  # <-- 新增导入
from ..interfaces.system import ITimeline, IEventBus  # <-- 新增导入
from ..interfaces.system.ilifecycle import ILifecycleAware
from typing import List, Tuple
import bisect
from ..models.timeline_model import TempoEvent, TimeSignatureEvent


class Timeline(ITimeline):
    """
    优化后的时间线
    管理速度和拍号变化
    """

    def __init__(self,
                 tempo: float = 120.0,
                 time_signature: Tuple[int, int] = (4, 4)):
        super().__init__()
        self._tempo_events: List[TempoEvent] = [
            TempoEvent(beat=0.0, bpm=tempo)
        ]
        self._time_signature_events: List[TimeSignatureEvent] = [
            TimeSignatureEvent(beat=0.0,
                               numerator=time_signature[0],
                               denominator=time_signature[1])
        ]

    def _get_children(self) -> List[ILifecycleAware]:
        return []

    @property
    def tempo(self) -> float:
        """获取初始速度"""
        return self._tempo_events[0].bpm

    def set_tempo(self, bpm: float):
        """设置初始速度"""
        self.set_tempo_at_beat(0.0, bpm)

    @property
    def time_signature(self) -> Tuple[int, int]:
        """获取初始拍号"""
        ts = self._time_signature_events[0]
        return (ts.numerator, ts.denominator)

    def set_time_signature(self, numerator: int, denominator: int):
        """设置初始拍号"""
        self.set_time_signature_at_beat(0.0, numerator, denominator)

    def set_tempo_at_beat(self, beat: float, bpm: float):
        """在指定节拍设置速度"""
        if beat < 0:
            return

        new_event = TempoEvent(beat=beat, bpm=bpm)
        idx = bisect.bisect_left(self._tempo_events, new_event)

        if idx < len(
                self._tempo_events) and self._tempo_events[idx].beat == beat:
            self._tempo_events[idx] = new_event
        else:
            self._tempo_events.insert(idx, new_event)

        if self.is_mounted:
            from ..models.event_model import TempoChanged
            self._event_bus.publish(TempoChanged(beat=beat, new_bpm=bpm))

    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        """在指定节拍设置拍号"""
        if beat < 0:
            return

        new_event = TimeSignatureEvent(beat=beat,
                                       numerator=numerator,
                                       denominator=denominator)
        idx = bisect.bisect_left(self._time_signature_events, new_event)

        if idx < len(self._time_signature_events
                     ) and self._time_signature_events[idx].beat == beat:
            self._time_signature_events[idx] = new_event
        else:
            self._time_signature_events.insert(idx, new_event)

        if self.is_mounted:
            from ..models.event_model import TimeSignatureChanged
            self._event_bus.publish(
                TimeSignatureChanged(beat=beat,
                                     numerator=numerator,
                                     denominator=denominator))

    def get_tempo_events(self) -> List[TempoEvent]:
        """获取所有速度事件"""
        return list(self._tempo_events)

    def get_time_signature_events(self) -> List[TimeSignatureEvent]:
        """获取所有拍号事件"""
        return list(self._time_signature_events)

    def beats_to_seconds(self, target_beats: float) -> float:
        """将节拍转换为秒"""
        if target_beats < 0:
            return 0.0

        total_seconds = 0.0
        current_beat = 0.0

        relevant_events = [
            e for e in self._tempo_events if e.beat <= target_beats
        ]
        if not relevant_events or target_beats > relevant_events[-1].beat:
            relevant_events.append(
                TempoEvent(beat=target_beats,
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
        """将秒转换为节拍"""
        if target_seconds < 0:
            return 0.0

        total_beats = 0.0
        current_seconds = 0.0
        current_beat = 0.0

        events_with_end = self._tempo_events + [
            TempoEvent(beat=float('inf'), bpm=self._tempo_events[-1].bpm)
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
        """将样本数转换为节拍"""
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        seconds = samples / sample_rate
        return self.seconds_to_beats(seconds)

    def beats_to_samples(self, beats: float, sample_rate: int) -> int:
        """将节拍转换为样本数"""
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        seconds = self.beats_to_seconds(beats)
        return round(seconds * sample_rate)

    def _get_tempo_at_beat(self, beat: float) -> float:
        """获取指定节拍的速度"""
        idx = bisect.bisect_right(self._tempo_events,
                                  TempoEvent(beat=beat, bpm=0.0))
        return self._tempo_events[idx - 1].bpm
