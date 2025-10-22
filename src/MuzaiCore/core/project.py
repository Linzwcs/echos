# file: src/MuzaiCore/core/project.py
import uuid
from typing import Dict, Optional, List

from ..interfaces import IProject, INode, IRouter, ITimeline, ICommandManager, IAudioEngine
from ..models.engine_model import TransportStatus


class Project(IProject):
    """
    The central aggregate root for all project-related state and logic.
    It owns all nodes, the router, timeline, and command manager.
    """

    def __init__(
            self,
            name: str,
            router: IRouter,
            timeline: ITimeline,
            command_manager: ICommandManager,
            engine: IAudioEngine,  # <-- Add engine to constructor
            project_id: Optional[str] = None):
        self._project_id = project_id or str(uuid.uuid4())
        self.name = name
        self._nodes: Dict[str, INode] = {}
        self._router = router
        self._timeline = timeline
        self._command_manager = command_manager
        self._transport_status = TransportStatus.STOPPED
        self._engine = engine  # <-- Store the engine
        self._engine.load_project(
            self)  # <-- Give the engine a reference back to the project
        self.tempo: float = 120.0
        self.time_signature: tuple[int, int] = (4, 4)

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

    def set_transport_status(self, status: TransportStatus):
        self._transport_status = status

    def get_node_by_id(self, node_id: str) -> Optional[INode]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[INode]:
        return list(self._nodes.values())

    def add_node(self, node: INode):
        if node.node_id in self._nodes:
            raise ValueError(f"Node with ID {node.node_id} already exists.")
        self._nodes[node.node_id] = node
        # The router should also be notified to add the node to its graph
        # self._router.add_node(node)

    def remove_node(self, node_id: str):
        if node_id not in self._nodes:
            raise ValueError(f"Node with ID {node_id} not found.")
        # The router must be updated before deleting the node
        # self._router.remove_node(node_id)
        del self._nodes[node_id]
