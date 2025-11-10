from abc import abstractmethod
from echos.models import ToolResponse
from .ibase_service import IService


class IHistoryService(IService):

    @abstractmethod
    def undo(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def redo(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def begin_macro(self, project_id: str, description: str) -> ToolResponse:
        pass

    @abstractmethod
    def end_macro(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def cancel_macro(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def get_undo_history(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def get_redo_history(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def can_undo(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def can_redo(self, project_id: str) -> ToolResponse:
        pass
