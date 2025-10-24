# file: src/MuzaiCore/models/parameter_model.py
from dataclasses import dataclass, field
from typing import Union, List, Tuple


class AutomationCurveType:
    """自动化曲线类型"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    SINE = "sine"
    SQUARE = "square"
    BEZIER = "bezier"


@dataclass
class AutomationPoint:
    """自动化点"""
    beat: float
    value: float
    curve_type: str = AutomationCurveType.LINEAR
    curve_shape: float = 0.0  # -1.0到1.0，控制曲线形状


@dataclass
class AutomationLane:
    """参数的自动化通道"""
    is_enabled: bool = True
    points: List[AutomationPoint] = field(default_factory=list)


@dataclass
class ParameterState:
    """参数的可序列化状态"""
    name: str
    value: Union[float, int, bool, str]
    automation_lane: AutomationLane = field(default_factory=AutomationLane)
