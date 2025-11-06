import uuid
from typing import Optional, List, Tuple
from .router import Router
from .timeline import Timeline
from .history.command_manager import CommandManager
from .event_bus import EventBus
from .parameter import Parameter
from .engine_controller import EngineController
from ..interfaces.system import IProject


class Project(IProject):

    def __init__(self, name: str, project_id: Optional[str] = None):
        super().__init__()
        self._project_id = project_id or f"project_{uuid.uuid4()}"
        self._name = name

        self._event_bus_instance = EventBus()
        self._router = Router()
        self._timeline = Timeline()
        self._command_manager = CommandManager()
        self._engine_controller = EngineController(router=self._router,
                                                   timeline=self._timeline)

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
    def engine_controller(self) -> EngineController:
        return self._engine_controller

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus_instance

    def initialize(self):
        self.mount(self._event_bus_instance)
        Parameter.initialize_batch_updater(self._event_bus_instance)
        print(f"Project '{self._name}': ✓ Initialized")

    def cleanup(self):
        print(f"Project '{self._name}': Cleaning up...")

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

    def _on_mount(self, event_bus: EventBus = None):
        self._event_bus = self._event_bus_instance

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self):
        return [self._router, self._timeline, self._engine_controller]

    def __repr__(self) -> str:
        stats = self.get_statistics()
        engine_status = "attached" if self._audio_engine else "no_engine"
        return (f"Project(name='{self.name}', "
                f"nodes={stats['node_count']}, "
                f"tempo={self.tempo}BPM, "
                f"status={self._transport_status.value}, "
                f"engine={engine_status})")
