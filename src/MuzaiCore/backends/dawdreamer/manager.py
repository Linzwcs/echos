# file: src/MuzaiCore/backends/dawdreamer/manager.py
"""
The DAW Manager for the DawDreamer backend.
This is the main Composition Root for this backend. It owns and wires up
all the DawDreamer-specific components.
"""
import dawdreamer as daw
from typing import Optional, Dict

from ...interfaces.system import IDAWManager, IProject, IProjectSerializer, INodeFactory
from ...models import ProjectState
from ...core.persistence import ProjectSerializer
from ...core.project import Project
from ...core.router import Router
from ...core.timeline import Timeline

from ..common.message_queue import RealTimeMessageQueue

from .registry import DawDreamerPluginRegistry
from .render_graph import DawDreamerRenderGraph
from .sync_controller import DawDreamerSyncController
from .transport import DawDreamerTransport
from .factory import DawDreamerNodeFactory


class DawDreamerDAWManager(IDAWManager):
    """
    Manages the lifecycle of projects and orchestrates all components
    for the DawDreamer backend.
    """

    def __init__(self,
                 registry: DawDreamerPluginRegistry,
                 sample_rate: int = 48000,
                 block_size: int = 512):
        print("Initializing DawDreamerDAWManager...")
        self._projects: Dict[str, IProject] = {}
        self._active_project_id: Optional[str] = None
        self._registry = registry
        self._sample_rate = sample_rate
        self._block_size = block_size

        # 1. Create the single, global DawDreamer RenderEngine.
        self._engine = daw.RenderEngine(sample_rate, block_size)
        self._engine.make_add_processor('master_out', [])
        # Connect the master bus to the physical output.
        self._engine.add_connection('master_out', 'output')
        print("  - Global DawDreamer RenderEngine created.")

        # 2. Instantiate backend-specific components.
        self._node_factory: INodeFactory = DawDreamerNodeFactory()

        # 3. Create the communication and sync components in order.
        self._message_queue = RealTimeMessageQueue()
        self._render_graph = DawDreamerRenderGraph(self._message_queue)
        self._sync_controller = DawDreamerSyncController(self._render_graph)
        print("  - RenderGraph, SyncController, and MessageQueue created.")

        # 4. Create the transport/playback controller.
        self._transport = DawDreamerTransport(self._engine,
                                              self._message_queue, sample_rate,
                                              block_size)
        print("  - Transport created.")

        # 5. Create the serializer for persistence.
        self._serializer: IProjectSerializer = ProjectSerializer(
            node_factory=self._node_factory, plugin_registry=self._registry)
        print("  - ProjectSerializer created.")

        print("DawDreamerDAWManager initialized successfully.")

    # --- Public Properties (as part of the backend's internal API) ---

    @property
    def plugin_registry(self) -> DawDreamerPluginRegistry:
        return self._registry

    @property
    def sync_controller(self) -> DawDreamerSyncController:
        return self._sync_controller

    @property
    def transport(self) -> DawDreamerTransport:
        return self._transport

    @property
    def node_factory(self) -> INodeFactory:
        return self._node_factory

    # --- IDAWManager Interface Implementation ---

    def create_project(self, name: str) -> IProject:
        if self._active_project_id:
            self.close_project(self._active_project_id)

        router = Router()  # Instantiate the event-aware router

        # *** THE KEY WIRING STEP ***
        # The SyncController listens directly to the Router's events.
        router.subscribe(self._sync_controller)

        project = Project(
            name=name,
            router=router,  # Pass the wired-up router
            timeline=Timeline(),
            command_manager=CommandManager(),
            engine=self._audio_engine)

        self._projects[project.project_id] = project
        self._active_project_id = project.project_id

        # Initial sync is no longer needed here, as adding nodes via services will trigger events.
        # However, for loading a project, the on_project_loaded approach is still best.

        print(
            f"DAWManager: Created project '{name}'. Router is now broadcasting to SyncController."
        )
        return project

    def get_project(self, project_id: str) -> Optional[IProject]:
        return self._projects.get(project_id)

    def close_project(self, project_id: str) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False

        if self.transport.is_playing:
            self.transport.stop()

        # Notify the sync controller to clear the render graph.
        self._sync_controller.on_project_closed(project)

        del self._projects[project_id]
        if self._active_project_id == project_id:
            self._active_project_id = None
            self._transport.set_project_timeline(None)  # Unlink timeline

        print(f"DAWManager: Closed project '{project.name}' ({project_id}).")
        return True

    def load_project_from_state(self, state: ProjectState) -> IProject:
        # If a project is already active, close it first.
        if self._active_project_id:
            self.close_project(self._active_project_id)

        print(f"DAWManager: Loading project from state '{state.name}'...")
        # 1. Use the serializer to reconstruct the domain model from the DTO.
        project = self._serializer.deserialize(state)

        # 2. Register the newly created project.
        self._projects[project.project_id] = project
        self._active_project_id = project.project_id

        # 3. Link its timeline to the transport.
        self._transport.set_project_timeline(project.timeline)

        # 4. CRITICAL: Synchronize the entire state of the new project to the audio engine.
        self._sync_project_to_engine(project)

        print(
            f"DAWManager: Successfully loaded and activated project '{project.name}'."
        )
        return project

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        project = self.get_project(project_id)
        if not project:
            return None

        # Use the serializer to convert the live domain object into a DTO.
        return self._serializer.serialize(project)

    # --- Backend-Specific Helper Methods ---

    def _sync_project_to_engine(self, project: IProject):
        """
        Synchronizes a complete project's state to the audio engine.
        This is a crucial step after loading a project from a file.
        """
        print(
            f"DAWManager: Syncing state of project '{project.name}' to DawDreamer engine..."
        )
        controller = self.sync_controller

        # 1. Ensure the render graph is cleared of any previous state.
        self._render_graph.clear()

        # 2. Add all nodes from the project to the render graph.
        # This includes tracks, buses, and the plugins they contain.
        all_nodes = project.get_all_nodes()
        for node in all_nodes:
            descriptor = getattr(node, 'descriptor',
                                 None)  # Get descriptor if it's a plugin
            controller.on_node_added(node, descriptor)

            # 3. Set all parameter values.
            # This is simplified; a full implementation would iterate all parameters.
            if hasattr(node, 'mixer_channel'):  # For tracks and buses
                mc = node.mixer_channel
                controller.on_parameter_changed(node.node_id, 'volume',
                                                mc.volume.value)
                controller.on_parameter_changed(node.node_id, 'pan',
                                                mc.pan.value)
                for plugin in mc.inserts:
                    for name, param in plugin.get_parameters().items():
                        controller.on_parameter_changed(
                            plugin.node_id, name, param.value)

        # 4. Add all routing connections to the render graph.
        for connection in project.router.get_all_connections():
            controller.on_connection_added(connection)

        print(f"DAWManager: Project state sync complete.")
