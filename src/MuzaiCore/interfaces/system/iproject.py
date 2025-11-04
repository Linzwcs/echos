# file: src/MuzaiCore/interfaces/IProject.py
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING, Tuple
from .inode import INode
from .irouter import IRouter
from .itimeline import IDomainTimeline
from .icommand import ICommandManager
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from ...models import TransportStatus


class IProject(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def project_id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def router(self) -> IRouter:
        pass

    @property
    @abstractmethod
    def timeline(self) -> IDomainTimeline:
        pass

    @property
    @abstractmethod
    def command_manager(self) -> ICommandManager:
        pass

    @property
    @abstractmethod
    def transport_status(self) -> TransportStatus:
        pass

    @abstractmethod
    def cleanup(self):
        pass
