from enum import Enum
from dataclasses import dataclass
from typing import List
from .node_state import NodeState
from ..router_model import Connection
from .base_state import BaseState


@dataclass(frozen=True)
class RouterState(BaseState):
    nodes: List[NodeState]
    connections: List[Connection]
