from abc import ABC, abstractmethod
from typing import Optional
from ...models.state_model import ProjectState


class IPersistenceService(ABC):

    @abstractmethod
    def save(self, state: ProjectState, file_path: str) -> None:
        """Saves a ProjectState DTO to a specified path."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> Optional[ProjectState]:
        """Loads a ProjectState DTO from a specified path."""
        pass
