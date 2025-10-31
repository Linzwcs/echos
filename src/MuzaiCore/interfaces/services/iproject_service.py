# file: src/MuzaiCore/services/IProjectService.py
from abc import ABC, abstractmethod
from MuzaiCore.models import ToolResponse
from .ibase_service import IService


class IProjectService(IService):

    @abstractmethod
    def create_project(self, name: str) -> ToolResponse:
        pass

    @abstractmethod
    def save_project(self, project_id: str, file_path: str) -> ToolResponse:
        pass

    @abstractmethod
    def load_project(self, file_path: str) -> ToolResponse:
        pass

    @abstractmethod
    def close_project(self, project_id: str) -> ToolResponse:
        pass
