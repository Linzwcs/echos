# file: src/MuzaiCore/interfaces/IProject.py
from abc import ABC, abstractmethod
from typing import Optional, List
from .INode import INode
from .IRouter import IRouter
from .ITimeline import ITimeline
from .ICommand import ICommandManager
from .IAudioEngine import IAudioEngine  # <-- Add this import

from ..models.engine_model import TransportStatus


class IProject(ABC):

    @property
    @abstractmethod
    def project_id(self) -> str:
        pass

    @property
    @abstractmethod
    def router(self) -> IRouter:
        pass

    @property
    @abstractmethod
    def timeline(self) -> ITimeline:
        pass

    @property
    @abstractmethod
    def command_manager(self) -> ICommandManager:
        pass

    @abstractmethod
    def get_node_by_id(self, node_id: str) -> Optional[INode]:
        pass

    @abstractmethod
    def get_all_nodes(self) -> List[INode]:
        pass

    @property
    @abstractmethod
    def transport_status(self) -> TransportStatus:
        pass

    @property
    @abstractmethod
    def engine(self) -> IAudioEngine:  # <-- Add this property
        """The audio engine instance associated with this project."""
        pass
