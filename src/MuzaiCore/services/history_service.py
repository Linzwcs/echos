# file: src/MuzaiCore/implementations/services/history_service.py

from ..models import ToolResponse
from ..interfaces.system import IDAWManager
from ..interfaces.service import IHistoryService


class HistoryService(IHistoryService):
    """
    历史管理服务
    
    特殊性：
    - 直接操作CommandManager
    - 不需要创建新的Command（它本身就是Command系统的接口）
    - 所有操作都是对Command历史的查询和控制
    """

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def undo(self, project_id: str) -> ToolResponse:
        """
        撤销操作
        
        直接调用CommandManager.undo()
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if not project.command_manager.can_undo():
            return ToolResponse("error", None, "Nothing to undo")

        try:
            project.command_manager.undo()
            return ToolResponse("success", None, "Undo successful")
        except Exception as e:
            return ToolResponse("error", None, f"Undo failed: {str(e)}")

    def redo(self, project_id: str) -> ToolResponse:
        """
        重做操作
        
        直接调用CommandManager.redo()
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if not project.command_manager.can_redo():
            return ToolResponse("error", None, "Nothing to redo")

        try:
            project.command_manager.redo()
            return ToolResponse("success", None, "Redo successful")
        except Exception as e:
            return ToolResponse("error", None, f"Redo failed: {str(e)}")

    def begin_macro(self, project_id: str, description: str) -> ToolResponse:
        """
        开始宏命令
        
        宏命令：将多个操作组合成单个可撤销单元
        适合Agent的"尝试"场景
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        try:
            project.command_manager.begin_macro_command(description)
            return ToolResponse("success", {"description": description},
                                f"Macro '{description}' started")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to begin macro: {str(e)}")

    def end_macro(self, project_id: str) -> ToolResponse:
        """
        结束宏命令
        
        提交宏中的所有操作为单个撤销单元
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        try:
            project.command_manager.end_macro_command()
            return ToolResponse("success", None, "Macro completed")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to end macro: {str(e)}")

    def cancel_macro(self, project_id: str) -> ToolResponse:
        """
        取消宏命令
        
        撤销宏中的所有操作
        Agent的"不喜欢，重来"功能
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        try:
            project.command_manager.cancel_macro_command()
            return ToolResponse("success", None, "Macro cancelled and undone")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to cancel macro: {str(e)}")

    def get_undo_history(self, project_id: str) -> ToolResponse:
        """获取撤销历史（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        history = project.command_manager.get_undo_history()
        return ToolResponse("success", {
            "history": history,
            "count": len(history)
        }, f"{len(history)} items in undo history")

    def get_redo_history(self, project_id: str) -> ToolResponse:
        """获取重做历史（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        history = project.command_manager.get_redo_history()
        return ToolResponse("success", {
            "history": history,
            "count": len(history)
        }, f"{len(history)} items in redo history")

    def can_undo(self, project_id: str) -> ToolResponse:
        """检查是否可以撤销（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        can_undo = project.command_manager.can_undo()
        return ToolResponse("success", {"can_undo": can_undo},
                            f"Can undo: {can_undo}")

    def can_redo(self, project_id: str) -> ToolResponse:
        """检查是否可以重做（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        can_redo = project.command_manager.can_redo()
        return ToolResponse("success", {"can_redo": can_redo},
                            f"Can redo: {can_redo}")
