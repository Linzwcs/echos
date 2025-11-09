from dataclasses import dataclass, field
from typing import Any, Optional
from .base_state import BaseState
from ..parameter_model import AutomationLane


@dataclass(frozen=True)
class ParameterState(BaseState):

    name: str
    value: Any
    default_value: Any
    min_value: Optional[Any]
    max_value: Optional[Any]
    unit: str
    automation_lane: AutomationLane = field(default_factory=AutomationLane)
