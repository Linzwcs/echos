# file: src/MuzaiCore/services/project_service.py
from ..agent.tools import tool
from ..interfaces import IDAWManager, IProjectService
from ..models import ToolResponse


class ProjectService(IProjectService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    @tool(
        category="project",
        description="Create a new music project",
        returns="Project ID and basic information",
        examples=['create_project(name="My Song")'],
    )
    def create_project(
        self,
        name: str,
        project_id: str = None,
        sample_rate: int = 48000,
        block_size: int = 8192,
        output_channels: int = 2,
    ) -> ToolResponse:
        try:
            project = self._manager.create_project(
                name=name,
                project_id=project_id,
                sample_rate=sample_rate,
                block_size=block_size,
                output_channels=output_channels)
            return ToolResponse(
                status="success",
                data={
                    "project_id": project.project_id,
                    "name": project.name
                },
                message=f"Project '{name}' created successfully.")
        except Exception as e:
            return ToolResponse("error", None, str(e))

    @tool(category="project",
          description="Save project to file",
          returns="Save operation result")
    def save_project(self, project_id: str, file_path: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Save functionality not implemented yet.")

    @tool(category="project",
          description="Load project from file",
          returns="Loaded project information")
    def load_project(self, file_path: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Load functionality not implemented yet.")

    @tool(category="project",
          description="Close an open project",
          returns="Close operation result")
    def close_project(self, project_id: str) -> ToolResponse:
        if self._manager.close_project(project_id):
            return ToolResponse("success", {"project_id": project_id},
                                f"Project '{project_id}' closed.")
        return ToolResponse("error", None,
                            f"Project '{project_id}' not found.")
