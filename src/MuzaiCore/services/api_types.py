# file: src/MuzaiCore/services/api_types.py
from typing import Any, NamedTuple, List, Dict, Tuple, Optional
from dataclasses import dataclass

class ToolResponse(NamedTuple):
    status: str
    data: Optional[Dict[str, Any]]
    message: str

@dataclass(frozen=True)
class PluginIdentifier:
    unique_id: str

@dataclass(frozen=True)
class NoteData:
    pitch: int
    velocity: int
    start_beat: float
    duration_beats: float

@dataclass(frozen=True)
class NodeInfo:
    node_id: str
    name: str
    node_type: str
