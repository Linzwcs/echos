# file: src/MuzaiCore/services/history_service.py
from ..interfaces import IDAWManager, IHistoryService
from ..models import ToolResponse


class HistoryService(IHistoryService):
    """历史记录服务的实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def undo(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if not project.command_manager.can_undo():
            return ToolResponse("success", {"can_undo": False},
                                "Nothing to undo.")

        project.command_manager.undo()
        return ToolResponse("success",
                            {"can_undo": project.command_manager.can_undo()},
                            "Undo successful.")

    def redo(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if not project.command_manager.can_redo():
            return ToolResponse("success", {"can_redo": False},
                                "Nothing to redo.")

        project.command_manager.redo()
        return ToolResponse("success",
                            {"can_redo": project.command_manager.can_redo()},
                            "Redo successful.")

    def get_undo_history(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        history = project.command_manager.get_undo_history()
        return ToolResponse("success", {"history": history},
                            "Undo history retrieved.")

    # 其他方法的实现...
    def get_redo_history(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        history = project.command_manager.get_redo_history()
        return ToolResponse("success", {"history": history},
                            "Redo history retrieved.")

    def can_undo(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        return ToolResponse("success",
                            {"can_undo": project.command_manager.can_undo()},
                            "")

    def can_redo(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        return ToolResponse("success",
                            {"can_redo": project.command_manager.can_redo()},
                            "")

    def begin_macro(self, project_id: str, description: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def end_macro(self, project_id: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def cancel_macro(self, project_id: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")
