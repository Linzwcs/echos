# file: src/MuzaiCore/implementations/mock/manager.py
from typing import Dict, Optional

# --- Core Component Imports ---
from ...core.project import Project
from ...core.track import MasterTrack  # Let's assume a dedicated MasterTrack exists
from ...subsystems.routing.router import Router
from ...subsystems.timeline.timeline import Timeline
from ...subsystems.commands.command_manager import CommandManager
from .audio_engine import MockAudioEngine

# --- Interface and Model Imports ---
from ...interfaces import (IDAWManager, IProject, IPluginRegistry,
                           IDeviceManager)
from ...models.project_model import ProjectState
from ...models.device_model import AudioDevice, MIDIDevice, IOChannel

# --- Mock Implementations for other managers ---
from .plugin import MockPluginRegistry
from .device_manager import MockDeviceManager  # <-- New mock component


class MockDAWManager(IDAWManager):
    """
    A mock implementation of the DAW manager that simulates a professional DAW environment.
    It manages project lifecycles and provides access to system-wide singletons
    like the plugin registry and device manager.
    """

    def __init__(self):
        self._projects: Dict[str, IProject] = {}
        # System-wide singletons that are shared across all projects
        self._plugin_registry: IPluginRegistry = MockPluginRegistry()
        self._device_manager: IDeviceManager = MockDeviceManager()

        # Initialize the singletons
        self._plugin_registry.scan_for_plugins()
        self._device_manager.scan_devices()
        print(
            "MockDAWManager: Initialized with mock plugin registry and device manager."
        )

    # +++ NEW: Provide access to system-wide managers +++
    @property
    def plugin_registry(self) -> IPluginRegistry:
        return self._plugin_registry

    @property
    def device_manager(self) -> IDeviceManager:
        return self._device_manager

    def create_project(self, name: str) -> IProject:
        # 1. Instantiate all subsystems for the new project
        router = Router()
        timeline = Timeline()
        command_manager = CommandManager()
        engine = MockAudioEngine()

        # 2. Create the project object, passing in all its dependencies
        new_project = Project(name=name,
                              router=router,
                              timeline=timeline,
                              command_manager=command_manager,
                              engine=engine)

        # 3. A professional DAW always starts with a master track
        # This should be an atomic operation, perhaps using a command.
        master_track = MasterTrack()  # Assumes a MasterTrack class exists
        new_project.add_node(master_track)

        # In a real system, you might also want to automatically route all
        # "un-routed" outputs to the master track's input. For mock, this is sufficient.
        print(f"MockDAWManager: Project '{name}' created with a master track.")

        self._projects[new_project.project_id] = new_project
        return new_project

    def get_project(self, project_id: str) -> Optional[IProject]:
        return self._projects.get(project_id)

    def close_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project:
            # Ensure engine thread is stopped before deleting
            project.engine.stop()
            del self._projects[project_id]
            print(f"MockManager: Closed project {project_id}")
            return True
        return False

    def load_project_from_state(self, state: ProjectState) -> IProject:
        # This is a complex operation that we will implement later.
        # It involves reconstructing all nodes, connections, etc. from the state.
        # For now, we'll just create a basic project.
        print(
            f"MockManager: [TODO] Loading project from state for {state.project_id}"
        )
        # Placeholder implementation
        project = self.create_project(state.name)
        # In a real implementation, you would overwrite the project_id and all its contents.
        return project

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        # This is the serialization counterpart to load_project_from_state.
        # We will also implement this in detail later.
        project = self.get_project(project_id)
        if not project:
            return None

        print(
            f"MockManager: [TODO] Serializing state for project {project_id}")
        # Placeholder implementation
        return ProjectState(project_id=project.project_id, name="Temp Name")
