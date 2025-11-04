from typing import Optional, Dict
from .project import Project
from ..interfaces import (
    IDAWManager,
    IProject,
    IProjectSerializer,
    IPluginRegistry,
)
from ..interfaces.system.ifactory import IEngineFactory, INodeFactory
from ..models import ProjectState


class DAWManager(IDAWManager):

    def __init__(
        self,
        project_serializer: IProjectSerializer,
        plugin_registry: IPluginRegistry,
        engine_factory: IEngineFactory,
        node_factory: INodeFactory,
    ):
        print("=" * 70)
        print("Initializing Generic Core DAW Manager...")
        print("=" * 70)

        self._projects: Dict[str, IProject] = {}
        self._engine_factory = engine_factory
        self._project_serializer = project_serializer
        self._plugin_registry = plugin_registry
        self._node_factory = node_factory

        print(
            "      ✓ Core Manager is ready. Backend is determined by injected factories."
        )
        print("=" * 70 + "\n")

    @property
    def plugin_registry(self) -> IPluginRegistry:
        return self._plugin_registry

    @property
    def node_factory(self) -> INodeFactory:
        return self._node_factory

    def create_project(
        self,
        name: str,
        sample_rate: int = 48000,
        block_size: int = 512,
    ) -> IProject:

        project = Project(name=name)
        project.initialize()
        engine = self._engine_factory.create_engine(sample_rate=sample_rate,
                                                    block_size=block_size)
        project.attach_engine(engine)
        self._projects[project.project_id] = project
        return project

    def load_project_from_state(self, state: ProjectState) -> IProject:

        project = self._project_serializer.deserialize(state)
        self._projects[project.project_id] = project
        return project

    def close_project(self, project_id: str) -> bool:

        if project_id not in self._projects:
            return False

        print(f"\nClosing project and destroying its stack ({project_id})...")
        project = self._projects[project_id]

        project.cleanup()

        del self._projects[project_id]
        return True

    def get_project(self, project_id: str) -> Optional[IProject]:
        return self._projects.get(project_id)

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:

        project = self.get_project(project_id)
        if not project:
            return None

        return self._project_serializer.serialize(project)
