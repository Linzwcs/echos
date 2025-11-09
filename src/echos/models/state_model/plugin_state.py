from dataclasses import dataclass, field
from typing import Dict
from .parameter_state import ParameterState
from .base_state import BaseState


@dataclass(frozen=True)
class PluginState(BaseState):
    instance_id: str
    unique_plugin_id: str
    is_enabled: bool = True
    parameters: Dict[str, ParameterState] = field(default_factory=dict)
