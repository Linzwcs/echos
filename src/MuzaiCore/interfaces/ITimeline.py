# 假设 ITimeline 位于此文件，或者将其移动到适当位置
# 请根据你的实际文件结构调整 ITimeline 的位置和导入
from abc import ABC, abstractmethod
from typing import List, Tuple
from MuzaiCore.models.timeline_model import TempoEvent, TimeSignatureEvent


class ITimeline(ABC):

    @abstractmethod
    def beats_to_seconds(self, beats: float) -> float:
        """将节拍数转换为秒。"""
        pass

    @abstractmethod
    def seconds_to_beats(self, seconds: float) -> float:
        """将秒转换为节拍数。"""
        pass

    @abstractmethod
    def get_tempo_events(self) -> List[TempoEvent]:
        """获取所有速度变化事件，按节拍排序。"""
        pass

    @abstractmethod
    def get_time_signature_events(self) -> List[TimeSignatureEvent]:
        """获取所有拍号变化事件，按节拍排序。"""
        pass

    @abstractmethod
    def set_tempo_at_beat(self, beat: float, bpm: float):
        """在指定节拍设置速度。"""
        pass

    @abstractmethod
    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        """在指定节拍设置拍号。"""
        pass

    @property
    @abstractmethod
    def tempo(self) -> float:
        """获取当前时间线（通常是0拍）的默认速度。"""
        pass

    @property
    @abstractmethod
    def time_signature(self) -> Tuple[int, int]:
        """获取当前时间线（通常是0拍）的默认拍号。"""
        pass

    @abstractmethod
    def samples_to_beats(self, samples: int, sample_rate: int) -> float:
        """将样本位置转换为节拍数。"""
        pass

    @abstractmethod
    def beats_to_samples(self, beats: float, sample_rate: int) -> int:
        """将节拍数转换为最接近的样本位置。"""
        pass
