# file: src/MuzaiCore/models/parameter_model.py
from dataclasses import dataclass, field
from typing import Union, List, Tuple


class AutomationCurveType:
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    # ... other curve types


@dataclass
class AutomationPoint:
    beat: float
    value: float
    # tension or curve_shape could be a float from -1.0 to 1.0
    curve_shape: float = 0.0
    curve_type: str = AutomationCurveType.LINEAR


@dataclass
class AutomationLane:
    """Represents all automation data for a single parameter."""
    is_enabled: bool = True
    points: List[AutomationPoint] = field(default_factory=list)


@dataclass
class ParameterState:
    name: str
    value: Union[float, int, bool, str]
    automation_lane: AutomationLane = field(default_factory=AutomationLane)
