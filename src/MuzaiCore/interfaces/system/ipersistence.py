# file: src/MuzaiCore/interfaces/IPersistence.py
from abc import ABC, abstractmethod
from typing import Optional
from ...models import ProjectState
from .iproject import IProject


class IProjectSerializer(ABC):

    @abstractmethod
    def serialize(self, project: 'IProject') -> ProjectState:
        pass

    @abstractmethod
    def deserialize(self, state: ProjectState) -> 'IProject':
        pass
