# file: src/MuzaiCore/models/project_model.py
from dataclasses import dataclass, field
from typing import List, Dict
from .node_model import NodeState
from .routing_model import Connection


@dataclass
class ProjectState:

    project_id: str
    name: str
    router: "Router"
    timeline: "Timeline"
