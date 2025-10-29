# file: src/MuzaiCore/interfaces/IDAWManager.py
from abc import ABC, abstractmethod
from typing import Optional

from .iproject import IProject
from ...models.project_model import ProjectState


class IDAWManager(ABC):
    """
    The top-level interface for managing the lifecycle of all DAW projects.
    This acts as the bridge between the service layer (Facade) and the
    concrete implementation (Mock, Real).
    """

    @abstractmethod
    def create_project(self, name: str) -> IProject:
        """
        Creates a new, fully initialized project instance and stores it.
        
        Args:
            name: The name of the new project.
        
        Returns:
            The created IProject instance.
        """
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[IProject]:
        """
        Retrieves a loaded project instance by its ID.
        
        Args:
            project_id: The unique ID of the project.
        
        Returns:
            The IProject instance if found, otherwise None.
        """
        pass

    @abstractmethod
    def close_project(self, project_id: str) -> bool:
        """
        Closes a project and releases its resources from memory.
        
        Args:
            project_id: The unique ID of the project to close.
            
        Returns:
            True if the project was found and closed, otherwise False.
        """
        pass

    @abstractmethod
    def load_project_from_state(self, state: ProjectState) -> IProject:
        """
        Reconstructs a project from its serialized state.
        
        Args:
            state: The ProjectState data transfer object.
            
        Returns:
            The fully reconstructed IProject instance.
        """
        pass

    @abstractmethod
    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        """
        Serializes a project's current state into a data transfer object.
        
        Args:
            project_id: The unique ID of the project to serialize.
            
        Returns:
            The ProjectState DTO if the project exists, otherwise None.
        """
        pass
