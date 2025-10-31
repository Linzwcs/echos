# file: src/MuzaiCore/services/project_service.py
from ..interfaces import IDAWManager, IProjectService
from ..models import ToolResponse


class ProjectService(IProjectService):
    """项目管理服务的具体实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def create_project(self, name: str) -> ToolResponse:
        """
        创建项目是系统级操作，它创建了CommandManager的上下文，
        因此它本身不通过Command执行。
        """
        try:
            project = self._manager.create_project(name)
            project.initialize()  # 挂载组件，启动参数批处理等
            return ToolResponse(
                status="success",
                data={
                    "project_id": project.project_id,
                    "name": project.name
                },
                message=f"Project '{name}' created successfully.")
        except Exception as e:
            return ToolResponse("error", None, str(e))

    # close, save, load 的实现会依赖于具体的持久化策略，这里暂时省略
    def save_project(self, project_id: str, file_path: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Save functionality not implemented yet.")

    def load_project(self, file_path: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Load functionality not implemented yet.")

    def close_project(self, project_id: str) -> ToolResponse:
        if self._manager.close_project(project_id):
            return ToolResponse("success", {"project_id": project_id},
                                f"Project '{project_id}' closed.")
        return ToolResponse("error", None,
                            f"Project '{project_id}' not found.")
