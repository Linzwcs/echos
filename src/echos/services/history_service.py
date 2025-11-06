from ..agent.tools import tool
from ..interfaces import IDAWManager, IHistoryService
from ..models import ToolResponse


class HistoryService:

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    @tool(category="history",
          description="Undo the last operation",
          returns="Undo result",
          examples=["undo(project_id='...')"])
    def undo(self, project_id: str) -> ToolResponse:
        """
        Undo the last operation.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Undo result with can_undo status
        """
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

    @tool(category="history",
          description="Redo the last undone operation",
          returns="Redo result")
    def redo(self, project_id: str) -> ToolResponse:
        """
        Redo the last undone operation.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Redo result with can_redo status
        """
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

    @tool(category="history",
          description="Get undo history",
          returns="List of undoable operations")
    def get_undo_history(self, project_id: str) -> ToolResponse:
        """
        Get undo history.
        
        Args:
            project_id: ID of the project
            
        Returns:
            List of undoable operations
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        history = project.command_manager.get_undo_history()
        return ToolResponse("success", {"history": history},
                            "Undo history retrieved.")

    @tool(category="history",
          description="Get redo history",
          returns="List of redoable operations")
    def get_redo_history(self, project_id: str) -> ToolResponse:
        """
        Get redo history.
        
        Args:
            project_id: ID of the project
            
        Returns:
            List of redoable operations
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        history = project.command_manager.get_redo_history()
        return ToolResponse("success", {"history": history},
                            "Redo history retrieved.")

    @tool(category="history",
          description="Check if undo is possible",
          returns="Boolean indicating if undo is available")
    def can_undo(self, project_id: str) -> ToolResponse:
        """
        Check if undo is possible.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Boolean can_undo status
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        return ToolResponse("success",
                            {"can_undo": project.command_manager.can_undo()},
                            "")

    @tool(category="history",
          description="Check if redo is possible",
          returns="Boolean indicating if redo is available")
    def can_redo(self, project_id: str) -> ToolResponse:
        """
        Check if redo is possible.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Boolean can_redo status
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        return ToolResponse("success",
                            {"can_redo": project.command_manager.can_redo()},
                            "")

    @tool(category="history",
          description="Begin a macro command (group multiple operations)",
          returns="Macro start confirmation")
    def begin_macro(self, project_id: str, description: str) -> ToolResponse:
        """
        Begin a macro command.
        
        Args:
            project_id: ID of the project
            description: Description of the macro operation
            
        Returns:
            Success confirmation
        """
        return ToolResponse("error", None,
                            "Macro commands not exposed via service yet")

    @tool(category="history",
          description="End the current macro command",
          returns="Macro end confirmation")
    def end_macro(self, project_id: str) -> ToolResponse:
        """
        End the current macro command.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Success confirmation
        """
        return ToolResponse("error", None,
                            "Macro commands not exposed via service yet")
