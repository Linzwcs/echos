# file: src/MuzaiCore/interfaces/IProject.py
from abc import ABC, abstractmethod
from .irouter import IRouter
from .itimeline import IDomainTimeline
from .icommand import ICommandManager
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from .iengine import IEngineController
from .iserializable import ISerializable


class IProject(
        ILifecycleAware,
        ISerializable,
        ABC,
):

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
    def engine_controller(self) -> IEngineController:
        pass

    @property
    @abstractmethod
    def command_manager(self) -> ICommandManager:
        pass

    @property
    @abstractmethod
    def event_bus(self) -> IEventBus:
        pass

    @abstractmethod
    def cleanup(self):
        pass
