from abc import abstractmethod
from typing import Optional
from .ibase_service import IService
from ...models.state_model import ProjectState


class IPersistenceService(IService):

    @abstractmethod
    def save(self, state: ProjectState, file_path: str) -> None:
        pass

    @abstractmethod
    def load(self, file_path: str) -> Optional[ProjectState]:
        pass
