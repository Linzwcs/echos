# file: src/MuzaiCore/interfaces/IProject.py
from abc import ABC, abstractmethod
from .irouter import IRouter
from .itimeline import IDomainTimeline
from .icommand import ICommandManager
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from .iengine import IEngine


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
    def engine(self) -> IEngine:
        pass

    @property
    @abstractmethod
    def command_manager(self) -> ICommandManager:
        pass

    @property
    @abstractmethod
    def event_bus(self) -> IEventBus:
        pass

    @property
    @abstractmethod
    def attach_engine(self, engine: IEngine):
        pass

    @property
    @abstractmethod
    def detach_engine(self, engine: IEngine):
        pass

    @abstractmethod
    def cleanup(self):
        pass
