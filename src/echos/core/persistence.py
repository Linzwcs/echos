# file: src/MuzaiCore/persistence/project_serializer.py
from typing import Optional, Dict, List, cast
from ..interfaces.system import (IProject, INode, IPlugin, ITrack,
                                 INodeFactory, IProjectSerializer,
                                 IPluginRegistry, IEventBus)
from ..models import (ProjectState, TrackState, PluginState, ParameterState,
                      NodeState, AnyClip)
from ..core.timeline import Timeline
from ..core.project import Project
from ..core.track import Track
from ..core.parameter import Parameter


class ProjectSerializer(IProjectSerializer):

    def __init__(self, node_factory: INodeFactory,
                 plugin_registry: IPluginRegistry):

        self._node_factory = node_factory
        self._registry = plugin_registry

    def serialize(self, project: IProject) -> dict:
        return {}

    def deserialize(self, state: ProjectState) -> IProject:

        return Project("mock")
