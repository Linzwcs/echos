import uuid
from typing import Dict, Optional, List, Tuple

from ..interfaces.system import (IProject, INode, IRouter, ITimeline,
                                 ICommandManager, IAudioEngine, IEventBus)
from ..models.engine_model import TransportStatus
from .router import Router
from .timeline import Timeline
from .history.command_manager import CommandManager
from .event_bus import EventBus
from .engine import AudioEngine


class Project(IProject):
    """
    The central aggregate root for all project-related state and logic.
    It owns the core components and delegates all graph/node management to the Router.
    """

    def __init__(
        self,
        name: str,
        project_id: str,
        sample_rate: int,
        block_size: int,
        router: Router,
        timeline: Timeline,
        command_manager: CommandManager,
        event_bus: EventBus,
    ):
        self._project_id = project_id or str(uuid.uuid4())
        self.name = name
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._router = router
        self._timeline = timeline
        self._command_manager = command_manager
        self._engine: Optional[AudioEngine] = None  # <-- 初始化为 None
        self._event_bus = event_bus
        self._transport_status = TransportStatus.STOPPED

    def set_engine(self, engine: AudioEngine):
        """将一个音频引擎附加到项目中。"""
        if self._engine is not None:
            print("Warning: An existing audio engine is being replaced.")
        self._engine = engine
        self._engine.set_project(self)  # 建立双向关联

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def router(self) -> IRouter:
        return self._router

    @property
    def timeline(self) -> ITimeline:
        return self._timeline

    @property
    def command_manager(self) -> ICommandManager:
        return self._command_manager

    @property
    def transport_status(self) -> TransportStatus:
        return self._transport_status

    @property
    def engine(self) -> AudioEngine:
        if self._engine:
            return self._engine
        else:
            return None

    # --- Time Structure (Delegated to Timeline) ---

    @property
    def tempo(self) -> float:
        """Gets the project's starting tempo from the timeline."""
        return self._timeline.tempo

    @tempo.setter
    def tempo(self, bpm: float):
        """Sets the project's starting tempo on the timeline."""
        self._timeline.set_tempo(bpm)

    @property
    def time_signature(self) -> Tuple[int, int]:
        """Gets the project's starting time signature from the timeline."""
        return self._timeline.time_signature

    @time_signature.setter
    def time_signature(self, value: Tuple[int, int]):
        """Sets the project's starting time signature on the timeline."""
        numerator, denominator = value
        self._timeline.set_time_signature(numerator, denominator)

    def set_engine(self, engine: AudioEngine):
        engine.load_event_bus(self._event_bus)
        self._engine = engine

    def get_node_by_id(self, node_id: str) -> Optional[INode]:
        """Retrieves a node by its ID, delegated from the router."""
        return self._router.get_node_by_id(node_id)

    def get_all_nodes(self) -> List[INode]:
        """Returns a list of all nodes, delegated from the router."""
        return self._router.get_all_nodes()

    def add_node(self, node: INode):
        """Adds a node to the project via the router."""
        self._router.add_node(node)

    def remove_node(self, node_id: str):
        """Removes a node from the project via the router."""
        self._router.remove_node(node_id)
