# file: src/MuzaiCore/services/IHistoryService.py
from abc import ABC, abstractmethod
from .api_types import ToolResponse

class IHistoryService(ABC):
    @abstractmethod
    def undo(self, project_id: str) -> ToolResponse: pass
    @abstractmethod
    def redo(self, project_id: str) -> ToolResponse: pass
