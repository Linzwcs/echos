from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ParameterType(Enum):

    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"
    STRING = "string"


class AutomationCurveType:

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    SINE = "sine"
    SQUARE = "square"
    BEZIER = "bezier"


@dataclass
class AutomationPoint:

    beat: float
    value: float
    curve_type: str = AutomationCurveType.LINEAR
    curve_shape: float = 0.0


@dataclass
class AutomationLane:

    is_enabled: bool = True
    points: List[AutomationPoint] = field(default_factory=list)
