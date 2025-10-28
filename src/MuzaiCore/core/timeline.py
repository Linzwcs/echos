# file: src/MuzaiCore/core/timeline.py
from typing import List, Tuple, NamedTuple, Optional
import bisect

from ..models.timeline_model import TempoEvent, TimeSignatureEvent
from ..interfaces.system import ITimeline


class TempoMap:
    """A simplified tempo map that assumes a constant tempo for now."""

    def __init__(self, initial_tempo: float = 120.0):
        self._tempo = initial_tempo

    def set_constant_tempo(self, bpm: float):
        if bpm <= 0:
            raise ValueError("BPM must be positive.")
        self._tempo = bpm

    def beats_to_seconds(self, beats: float) -> float:
        return (beats * 60.0) / self._tempo

    def seconds_to_beats(self, seconds: float) -> float:
        return (seconds * self._tempo) / 60.0


class Timeline(ITimeline):
    """
    Timeline 的具体实现，负责处理节拍和秒之间的转换，并支持时间线上的速度和拍号变化。
    """

    def __init__(self,
                 tempo: float = 120.0,
                 time_signature: Tuple[int, int] = (4, 4)):
        # 速度事件列表，始终包含一个在 0 拍的初始速度
        self._tempo_events: List[TempoEvent] = [
            TempoEvent(beat=0.0, bpm=tempo)
        ]
        # 拍号事件列表，始终包含一个在 0 拍的初始拍号
        self._time_signature_events: List[TimeSignatureEvent] = [
            TimeSignatureEvent(beat=0.0,
                               numerator=time_signature[0],
                               denominator=time_signature[1])
        ]

    @property
    def tempo(self) -> float:
        """获取时间线开始时的速度 (0 拍)。"""
        return self._tempo_events[0].bpm

    def set_tempo(self, bpm: float):
        """设置时间线开始时的速度 (0 拍)。"""
        self.set_tempo_at_beat(0.0, bpm)

    @property
    def time_signature(self) -> Tuple[int, int]:
        """获取时间线开始时的拍号 (0 拍)。"""
        ts = self._time_signature_events[0]
        return (ts.numerator, ts.denominator)

    def set_time_signature(self, numerator: int, denominator: int):
        """设置时间线开始时的拍号 (0 拍)。"""
        self.set_time_signature_at_beat(0.0, numerator, denominator)

    def _add_or_update_event(self, event_list: List[NamedTuple],
                             new_event: NamedTuple):
        """
        通用的辅助方法，用于在排序事件列表中添加或更新事件。
        如果指定节拍已存在事件，则更新；否则插入新事件并保持排序。
        """
        idx = bisect.bisect_left(event_list, new_event)
        if idx < len(event_list) and event_list[idx].beat == new_event.beat:
            # 节拍已存在，更新
            event_list[idx] = new_event
        else:
            # 节拍不存在，插入
            event_list.insert(idx, new_event)

    def set_tempo_at_beat(self, beat: float, bpm: float):
        """
        在指定节拍设置速度。
        如果 beat < 0，忽略。
        如果 beat 已经有速度事件，则更新。
        否则插入新事件并保持列表排序。
        """
        if beat < 0:
            return

        new_tempo_event = TempoEvent(beat=beat, bpm=bpm)
        self._add_or_update_event(self._tempo_events, new_tempo_event)

    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        """
        在指定节拍设置拍号。
        如果 beat < 0，忽略。
        如果 beat 已经有拍号事件，则更新。
        否则插入新事件并保持列表排序。
        """
        if beat < 0:
            return

        new_ts_event = TimeSignatureEvent(beat=beat,
                                          numerator=numerator,
                                          denominator=denominator)
        self._add_or_update_event(self._time_signature_events, new_ts_event)

    def get_tempo_events(self) -> List[TempoEvent]:
        """返回所有速度事件的副本。"""
        return list(self._tempo_events)

    def get_time_signature_events(self) -> List[TimeSignatureEvent]:
        """返回所有拍号事件的副本。"""
        return list(self._time_signature_events)

    def _get_active_tempo_at_beat(self, beat: float) -> float:
        """获取在指定节拍生效的速度。"""
        # 查找第一个 beat > target_beat 的事件的索引
        # 然后取前一个事件的速度
        idx = bisect.bisect_right(self._tempo_events,
                                  TempoEvent(beat=beat, bpm=0.0))
        # bisect_right 返回一个索引 'i'，使得对于列表中的所有 'e'，
        # a[:i] 中的所有 e.beat <= new_event.beat，a[i:] 中的所有 e.beat > new_event.beat。
        # 所以我们想要的是 index 'idx - 1' 处的事件
        return self._tempo_events[idx - 1].bpm

    def _get_active_time_signature_at_beat(self,
                                           beat: float) -> TimeSignatureEvent:
        """获取在指定节拍生效的拍号。"""
        idx = bisect.bisect_right(
            self._time_signature_events,
            TimeSignatureEvent(beat=beat, numerator=0, denominator=0))
        return self._time_signature_events[idx - 1]

    def beats_to_seconds(self, target_beats: float) -> float:
        """
        将节拍数转换为秒。考虑所有速度变化。
        """
        if target_beats < 0:
            return 0.0

        total_seconds = 0.0
        current_beat = 0.0

        # 获取所有在 target_beats 之前的速度事件，包括 target_beats 处或之后的第一个事件
        # 这确保我们覆盖了所有相关的速度段
        relevant_tempo_events = [
            e for e in self._tempo_events if e.beat <= target_beats
        ]
        # 如果 target_beats 之后还有事件，确保我们能找到其生效的速度
        if target_beats > relevant_tempo_events[
                -1].beat:  # 如果 target_beats 在最后一个事件之后
            relevant_tempo_events.append(
                TempoEvent(beat=target_beats,
                           bpm=self._get_active_tempo_at_beat(target_beats)))

        for i in range(len(relevant_tempo_events) - 1):
            start_event = relevant_tempo_events[i]
            end_event = relevant_tempo_events[i + 1]

            # 计算当前段的结束节拍 (不能超过 target_beats)
            segment_end_beat = min(end_event.beat, target_beats)

            if segment_end_beat > current_beat:
                # 使用当前段的速度计算持续时间
                beats_in_segment = segment_end_beat - current_beat
                tempo_for_segment = start_event.bpm
                total_seconds += (beats_in_segment / tempo_for_segment) * 60.0

            current_beat = segment_end_beat
            if current_beat >= target_beats:
                break  # 已经达到或超过目标节拍

        # 处理最后一个段，如果 target_beats 落在最后一个已知的速度事件之后
        if current_beat < target_beats:
            last_tempo = self._get_active_tempo_at_beat(target_beats)
            beats_in_last_segment = target_beats - current_beat
            total_seconds += (beats_in_last_segment / last_tempo) * 60.0

        return total_seconds

    def seconds_to_beats(self, target_seconds: float) -> float:
        """
        将秒转换为节拍数。考虑所有速度变化。
        """
        if target_seconds < 0:
            return 0.0

        total_beats = 0.0
        current_seconds = 0.0
        current_beat_pos = 0.0  # 用于追踪当前计算到的节拍位置

        # 获取所有速度事件，并加上一个代表时间线末尾的虚拟事件，方便循环处理
        # 最后一个事件的速度将延续到无限
        tempo_events_with_end = self._tempo_events + [
            TempoEvent(beat=float('inf'), bpm=self._tempo_events[-1].bpm)
        ]

        for i in range(len(tempo_events_with_end) - 1):
            start_event = tempo_events_with_end[i]
            end_event = tempo_events_with_end[i + 1]

            tempo_for_segment = start_event.bpm
            # 计算当前速度段的总秒数（如果它能持续到下一个速度事件）
            # 注意：如果 end_event.beat 是 float('inf')，那么 segment_total_beats 也是 inf
            segment_total_beats = end_event.beat - current_beat_pos

            # 避免除以零或负值
            if tempo_for_segment <= 0:
                # 遇到无效的bpm，跳过此段或报错
                # 实际应用中可能需要更复杂的错误处理
                continue

            segment_total_seconds = (segment_total_beats /
                                     tempo_for_segment) * 60.0

            if current_seconds + segment_total_seconds >= target_seconds:
                # 目标秒数落在当前速度段内
                remaining_seconds = target_seconds - current_seconds
                beats_in_remaining_seconds = (remaining_seconds *
                                              tempo_for_segment) / 60.0
                total_beats += beats_in_remaining_seconds
                return total_beats
            else:
                # 目标秒数超出当前速度段，累加当前段的秒数和节拍
                total_beats += segment_total_beats
                current_seconds += segment_total_seconds
                current_beat_pos = end_event.beat  # 更新当前节拍位置

        return total_beats  # 应该不会执行到这里，除非 target_seconds 极长

    def samples_to_beats(self, samples: int, sample_rate: int) -> float:
        """
        将样本位置转换为节拍数。
        这是一个两步转换：samples -> seconds -> beats。
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")

        # 步骤 1: 将样本数转换为秒
        # 这是纯粹的物理时间转换，与速度无关
        seconds = samples / sample_rate

        # 步骤 2: 使用已有的方法将秒转换为节拍
        # 这一步会处理所有的速度变化
        return self.seconds_to_beats(seconds)

    def beats_to_samples(self, beats: float, sample_rate: int) -> int:
        """
        将节拍数转换为最接近的样本位置。
        这是一个两步转换：beats -> seconds -> samples。
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")

        # 步骤 1: 使用已有的方法将节拍转换为秒
        # 这一步会处理所有的速度变化
        seconds = self.beats_to_seconds(beats)

        # 步骤 2: 将秒转换为样本数
        # 这是纯粹的物理时间转换，与速度无关
        samples = seconds * sample_rate

        # 返回最接近的整数样本位置，因为样本是离散的
        return round(samples)
