# file: src/MuzaiCore/services/IProjectService.py
from abc import ABC, abstractmethod
from .api_types import ToolResponse

class IProjectService(ABC):
    @abstractmethod
    def create_project(self, name: str) -> ToolResponse: pass
