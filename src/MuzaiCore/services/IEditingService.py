# file: src/MuzaiCore/services/IEditingService.py
from abc import ABC, abstractmethod
from typing import Any, List
from .api_types import ToolResponse, NoteData

class IEditingService(ABC):
    @abstractmethod
    def set_parameter_value(self, project_id: str, node_id: str, parameter_name: str, value: Any) -> ToolResponse: pass
    
    @abstractmethod
    def add_notes_to_clip(self, project_id: str, clip_id: str, notes: List[NoteData]) -> ToolResponse: pass
