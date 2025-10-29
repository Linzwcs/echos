# file: src/MuzaiCore/implementations/services/project_service.py
from typing import Optional
from ..interfaces.services import IProjectService
from ..models import ToolResponse, ProjectState
from ..interfaces import IDAWManager


class ProjectService(IProjectService):
    """
    项目管理服务（Command驱动）
    
    操作类型：
    - 创建/加载项目：需要特殊处理（不在项目内部）
    - 保存/关闭：不需要撤销
    - 查询：直接访问
    """

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def create_project(self, name: str) -> ToolResponse:
        """
        创建新项目
        
        注意：这个操作在Manager层面，不在单个Project内部
        所以不使用Command（无法撤销项目创建本身）
        
        但可以考虑在Manager层实现ProjectCommand系统
        """
        try:
            project = self._manager.create_project(name)
            return ToolResponse(
                "success", {
                    "project_id": project.project_id,
                    "name": name,
                    "tempo": project.tempo,
                    "time_signature": project.time_signature
                }, f"Project '{name}' created successfully")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to create project: {str(e)}")

    def save_project(self, project_id: str, file_path: str) -> ToolResponse:
        """
        保存项目到文件
        
        保存操作不需要Command：
        - 不修改项目状态（只是序列化）
        - 不需要撤销
        """
        try:
            project_state = self._manager.get_project_state(project_id)
            if not project_state:
                return ToolResponse("error", None,
                                    f"Project {project_id} not found")

            # 在真实实现中，这里会序列化到磁盘
            # import json
            # with open(file_path, 'w') as f:
            #     json.dump(project_state, f)

            print(f"Saving project {project_id} to {file_path}")

            return ToolResponse("success", {
                "project_id": project_id,
                "file_path": file_path
            }, f"Project saved to {file_path}")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to save project: {str(e)}")

    def load_project(self, file_path: str) -> ToolResponse:
        """
        从文件加载项目
        
        加载操作创建新项目，不需要Command
        """
        try:
            # 在真实实现中，这里会从磁盘反序列化
            # import json
            # with open(file_path, 'r') as f:
            #     state_dict = json.load(f)
            #     project_state = ProjectState(**state_dict)

            print(f"Loading project from {file_path}")

            # 模拟加载
            project_state = ProjectState(project_id="loaded_project_id",
                                         name="Loaded Project")
            project = self._manager.load_project_from_state(project_state)

            return ToolResponse("success", {
                "project_id": project.project_id,
                "file_path": file_path
            }, f"Project loaded from {file_path}")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to load project: {str(e)}")

    def close_project(self, project_id: str) -> ToolResponse:
        """
        关闭项目
        
        关闭操作不需要Command：
        - 释放资源
        - 不需要撤销（可以重新load）
        """
        try:
            success = self._manager.close_project(project_id)
            if success:
                return ToolResponse("success", None,
                                    f"Project {project_id} closed")
            else:
                return ToolResponse("error", None,
                                    f"Project {project_id} not found")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to close project: {str(e)}")

    def get_project_info(self, project_id: str) -> ToolResponse:
        """
        获取项目基本信息（查询操作）
        
        查询不需要Command：直接访问
        """
        try:
            project = self._manager.get_project(project_id)
            if not project:
                return ToolResponse("error", None,
                                    f"Project {project_id} not found")

            return ToolResponse(
                "success", {
                    "project_id": project.project_id,
                    "name": project.name,
                    "tempo": project.tempo,
                    "time_signature": project.time_signature,
                    "transport_status": project.transport_status.value,
                    "node_count": len(project.get_all_nodes())
                }, "Project information retrieved")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to get project info: {str(e)}")
