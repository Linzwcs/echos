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
        """
        将一个活动的 IProject 对象转换为 ProjectState DTO。
        """
        print(f"Serializing project: '{project.project_name}'")
        return {}

    def deserialize(self, state: ProjectState) -> IProject:
        """
        从 ProjectState DTO 创建并返回一个活动的 IProject 对象。
        注意：反序列化通常需要 EventBus，但此 mock 实现中省略了它以符合原始 __init__ 签名。
        在实际应用中，可能需要通过方法参数传入 EventBus。
        """
        # 创建一个新的 Project 实例
        # 假设 Project 构造函数需要这些服务
        return Project("mock")
