# file: src/MuzaiCore/models/timeline_model.py
from dataclasses import dataclass
from typing import NamedTuple, Tuple


class TempoEvent(NamedTuple):
    """
    表示时间线上的一个速度变化点。
    beat: 发生速度变化的节拍位置 (float)。
    bpm: 该点开始生效的新速度 (float)。
    """
    beat: float
    bpm: float


class TimeSignatureEvent(NamedTuple):
    """
    表示时间线上的一个拍号变化点。
    beat: 发生拍号变化的节拍位置 (float)。
    numerator: 新拍号的分子 (int)。
    denominator: 新拍号的分母 (int)。
    """
    beat: float
    numerator: int
    denominator: int
