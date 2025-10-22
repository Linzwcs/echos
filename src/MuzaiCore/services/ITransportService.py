# file: src/MuzaiCore/services/ITransportService.py
from abc import ABC, abstractmethod
from .api_types import ToolResponse

class ITransportService(ABC):
    @abstractmethod
    def play(self, project_id: str) -> ToolResponse: pass
    @abstractmethod
    def stop(self, project_id: str) -> ToolResponse: pass
    @abstractmethod
    def set_tempo(self, project_id: str, bpm: float) -> ToolResponse: pass
