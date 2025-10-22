# file: src/MuzaiCore/models/project_model.py
from dataclasses import dataclass, field
from typing import List, Dict
from .node_model import NodeState
from ..subsystems.routing.routing_types import Connection


@dataclass
class ProjectState:
    """The complete, serializable state of a project."""
    project_id: str
    name: str
    nodes: Dict[str, NodeState] = field(default_factory=dict)
    routing_graph: List[Connection] = field(default_factory=list)
    tempo: float = 120.0
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
