import uuid
from typing import Optional, List, Tuple

from .router import Router
from .timeline import Timeline
from .history.command_manager import CommandManager
from .event_bus import EventBus
from .parameter import Parameter
from ..interfaces.system import (IProject, INode, IRouter, IDomainTimeline,
                                 ICommandManager, IEngine, IEventBus)
from ..interfaces.system.ilifecycle import ILifecycleAware
from ..models.engine_model import TransportStatus


class Project(IProject):

    def __init__(self, name: str, project_id: Optional[str] = None):
        super().__init__()
        self._project_id = project_id or f"project_{uuid.uuid4()}"
        self._name = name

        self._event_bus_instance = EventBus()
        self._router = Router()
        self._timeline = Timeline()
        self._command_manager = CommandManager()

        self._transport_status = TransportStatus.STOPPED
        self._current_beat = 0.0

        self._audio_engine: Optional['IEngine'] = None
        self.initialize()

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def router(self) -> Router:
        return self._router

    @property
    def timeline(self) -> Timeline:
        return self._timeline

    @property
    def command_manager(self) -> CommandManager:
        return self._command_manager

    @property
    def engine(self) -> IEngine:
        return self._audio_engine

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus_instance

    def initialize(self):
        self.mount(self._event_bus_instance)
        Parameter.initialize_batch_updater(self._event_bus_instance)
        print(f"Project '{self._name}': ✓ Initialized")

    def attach_engine(self, engine: IEngine):
        if not self.is_mounted:
            raise RuntimeError(
                "Project must be initialized before attaching engine")

        if self._audio_engine:
            print("Project: Replacing existing engine")
            self.detach_engine()

        self._audio_engine = engine
        engine.mount(self._event_bus_instance)
        from ..models.event_model import ProjectLoaded
        self._event_bus_instance.publish(
            ProjectLoaded(timeline_state=self._timeline.timeline_state))

        print(f"Project '{self._name}': ✓ Engine attached")

    def detach_engine(self):
        if not self._audio_engine:
            return

        from ..models.event_model import ProjectClosed
        self._event_bus_instance.publish(ProjectClosed())

        self._audio_engine.unmount()
        self._audio_engine = None
        print(f"Project '{self._name}': ✓ Engine detached")

    def cleanup(self):
        print(f"Project '{self._name}': Cleaning up...")

        if self._audio_engine:
            self.detach_engine()

        self.unmount()

        Parameter.shutdown_batch_updater()

        self._command_manager.clear()

        self._event_bus_instance.clear()

        print(f"Project '{self._name}': ✓ Cleaned up")

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []

        if self._router.has_cycle():
            errors.append("Graph contains cycles")

        if self.tempo <= 0:
            errors.append(f"Invalid tempo: {self.tempo}")

        for node in self.get_all_nodes():
            if not node.node_id:
                errors.append(f"Node without ID: {type(node).__name__}")

        return len(errors) == 0, errors

    def get_statistics(self) -> dict:

        nodes = self.get_all_nodes()
        connections = self._router.get_all_connections()

        node_types = {}
        for node in nodes:
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1

        return {
            "project_id": self._project_id,
            "name": self.name,
            "tempo": self.tempo,
            "time_signature": self.time_signature,
            "transport_status": self._transport_status.value,
            "current_beat": self._current_beat,
            "node_count": len(nodes),
            "node_types": node_types,
            "connection_count": len(connections),
            "has_cycle": self._router.has_cycle(),
            "has_audio_engine": self._audio_engine is not None,
        }

    def _on_mount(self, event_bus: IEventBus = None):
        self._event_bus = self._event_bus_instance

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self):
        return [self._router, self._timeline]

    def __repr__(self) -> str:
        stats = self.get_statistics()
        engine_status = "attached" if self._audio_engine else "no_engine"
        return (f"Project(name='{self.name}', "
                f"nodes={stats['node_count']}, "
                f"tempo={self.tempo}BPM, "
                f"status={self._transport_status.value}, "
                f"engine={engine_status})")
