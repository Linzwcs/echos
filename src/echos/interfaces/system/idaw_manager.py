# file: src/MuzaiCore/interfaces/IDAWManager.py
from abc import ABC, abstractmethod
from typing import Optional

from .iproject import IProject
from ...models.project_model import ProjectState


class IDAWManager(ABC):

    @abstractmethod
    def create_project(
        self,
        name: str,
        project_id: str,
        sample_rate: int,
        block_size: int,
        output_channels: int,
    ) -> IProject:
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[IProject]:
        pass

    @abstractmethod
    def close_project(self, project_id: str) -> bool:
        pass

    @abstractmethod
    def load_project_from_state(self, state: ProjectState) -> IProject:
        pass

    @abstractmethod
    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        pass
