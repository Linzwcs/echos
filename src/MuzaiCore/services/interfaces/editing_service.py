# file: src/MuzaiCore/services/IEditingService.py
from abc import ABC, abstractmethod
from typing import Any, List, Dict
from MuzaiCore.models import ToolResponse
from .base_service import IService


class IEditingService(IService):

    @abstractmethod
    def set_parameter_value(self, project_id: str, node_id: str,
                            parameter_name: str, value: Any) -> ToolResponse:
        pass

    @abstractmethod
    def add_automation_point(self, project_id: str, node_id: str,
                             parameter_name: str, beat: float,
                             value: Any) -> ToolResponse:
        pass

    @abstractmethod
    def create_midi_clip(self,
                         project_id: str,
                         track_id: str,
                         start_beat: float,
                         duration_beats: float,
                         name: str = "MIDI Clip") -> ToolResponse:
        pass

    @abstractmethod
    def add_notes_to_clip(self, project_id: str, clip_id: str,
                          notes: List[Dict[str, Any]]) -> ToolResponse:
        pass
