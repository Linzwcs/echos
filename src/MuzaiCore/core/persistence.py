# file: src/MuzaiCore/persistence/project_serializer.py
from typing import Optional, Dict, List

from ..interfaces.system import (IProject, INode, IPlugin, ITrack,
                                 INodeFactory, IProjectSerializer,
                                 IPluginRegistry, IEventBus)
from ..models import (ProjectState, TrackState, PluginState, ParameterState,
                      NodeState, AnyClip)
from ..core.timeline import Timeline
from ..core.project import Project


class ProjectSerializer(IProjectSerializer):
    """
    一个无状态的服务，负责在活动的 Project 对象和可序列化的 ProjectState DTO 之间进行转换。
    它自身不持有任何项目相关的状态。
    """

    def __init__(self, node_factory: INodeFactory,
                 plugin_registry: IPluginRegistry):
        """
        序列化器是无状态的。它只持有对其他共享的、无状态的服务（工厂和注册表）的引用。
        它不持有 EventBus。
        """
        self._node_factory = node_factory
        self._registry = plugin_registry
