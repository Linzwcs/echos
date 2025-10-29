# file: src/MuzaiCore/persistence/project_serializer.py
from ..interfaces.system.iproject import IProject
from ..interfaces.system.inode_factory import INodeFactory
from ..interfaces.system.ipersistence import IProjectSerializer
from ..interfaces.system.iplugin_registry import IPluginRegistry  # <-- 新增导入
from ..models import ProjectState, TrackState, PluginState, ParameterState
from .timeline import Timeline
from .project import Project
#from .history.command_manager import


class ProjectSerializer(IProjectSerializer):
    """
    Handles the conversion between live Project objects and serializable
    ProjectState DTOs.
    """

    def __init__(self, node_factory: INodeFactory,
                 plugin_registry: IPluginRegistry):  # <-- 修改构造函数
        # The factory is crucial for deserialization, as it knows how to create
        # the correct backend-specific node instances.
        self._node_factory = node_factory
        # The registry is needed to find plugin blueprints during deserialization.
        self._registry = plugin_registry  # <-- 存储注册表

    def serialize(self, project: IProject) -> ProjectState:
        """Converts a live Project object into a ProjectState DTO."""
        nodes_state = {}
        for node in project.get_all_nodes():
            serialized_node = self._serialize_node(node)
            if serialized_node:
                nodes_state[node.node_id] = serialized_node

        routing_graph = project.router.get_all_connections()

        return ProjectState(
            project_id=project.project_id,
            name=project.name,
            nodes=nodes_state,
            routing_graph=routing_graph,
            tempo=project.timeline.tempo,
            time_signature_numerator=project.timeline.time_signature[0],
            time_signature_denominator=project.timeline.time_signature[1],
        )

    def deserialize(self, state: ProjectState) -> IProject:
        """Rebuilds a live Project object from a ProjectState DTO."""
        from ..core.project import Project
        from ..core.router import Router
        from ..core.history.command_manager import CommandManager
        from ..backends.dawdreamer.engine import DawDreamerAudioEngine
        from ..backends.dawdreamer.transport import DawDreamerTransport
        from ..backends.common.message_queue import RealTimeMessageQueue
        import dawdreamer as daw

        # 1. Create the basic project structure
        # 在反序列化时，我们需要重建项目的依赖
        # 这部分逻辑与 DawDreamerManager 中的相似
        # 注意: 此处为简化实现，实际应用中可能需要更灵活的引擎注入
        sample_rate = 48000
        block_size = 512
        dd_engine = daw.RenderEngine(sample_rate, block_size)
        queue = RealTimeMessageQueue()
        transport = DawDreamerTransport(dd_engine, queue, sample_rate,
                                        block_size)
        engine = DawDreamerAudioEngine(transport=transport,
                                       render_graph=None)  # RenderGraph稍后同步

        new_project = Project(
            name=state.name,
            project_id=state.project_id,
            router=Router(),
            command_manager=CommandManager(),
            timeline=Timeline(state.tempo, (state.time_signature_numerator,
                                            state.time_signature_denominator)),
            engine=engine)

        # 2. Recreate all nodes using the factory
        # 必须先创建所有节点，因为路由连接依赖它们
        nodes_map = {}
        for node_id, node_state in state.nodes.items():
            recreated_node = self._deserialize_node(node_state)
            if recreated_node:
                nodes_map[node_id] = recreated_node
                new_project.add_node(recreated_node)

        # 3. Re-establish all routing connections
        for connection in state.routing_graph:
            new_project.router.connect(connection.source_port,
                                       connection.dest_port)

        return new_project

    def _serialize_node(self, node: 'INode') -> 'NodeState':
        """Helper to serialize a single node."""
        from ..core.domain.track import ITrack
        from ..core.plugin import IPlugin

        if isinstance(node, ITrack):
            plugins = [
                self._serialize_plugin(p) for p in node.mixer_channel.inserts
            ]
            return TrackState(
                node_id=node.node_id,
                name=node.name,
                track_type=type(node).__name__,
                clips=list(node.clips),
                plugins=plugins,
                volume=ParameterState(name="volume",
                                      value=node.mixer_channel.volume.value),
                pan=ParameterState(name="pan",
                                   value=node.mixer_channel.pan.value),
                is_muted=node.mixer_channel.is_muted,
                is_solo=node.mixer_channel.is_solo,
            )
        elif isinstance(node, IPlugin):
            # 插件现在作为顶级节点被序列化
            return self._serialize_plugin(node)
        return None

    def _serialize_plugin(self, plugin: 'IPlugin') -> PluginState:
        """Helper to serialize a plugin instance."""
        params = {
            name: ParameterState(name=name, value=p.value)
            for name, p in plugin.get_parameters().items()
        }
        return PluginState(
            instance_id=plugin.node_id,
            unique_plugin_id=plugin.descriptor.unique_plugin_id,
            is_enabled=plugin.is_enabled,
            parameters=params,
        )

    def _deserialize_node(self, node_state: 'NodeState') -> 'INode':
        """Helper to deserialize a single node using the factory."""
        if isinstance(node_state, TrackState):
            track_type_name = node_state.track_type.lower()
            node = None
            if "instrument" in track_type_name:
                node = self._node_factory.create_instrument_track(
                    node_state.name)
            elif "audio" in track_type_name:
                node = self._node_factory.create_audio_track(node_state.name)
            elif "bus" in track_type_name:
                node = self._node_factory.create_bus_track(node_state.name)

            if not node:
                return None

            # Restore state
            node._node_id = node_state.node_id
            node.clips = set(node_state.clips)
            node.mixer_channel.volume._set_value_internal(
                node_state.volume.value)
            node.mixer_channel.pan._set_value_internal(node_state.pan.value)
            node.mixer_channel.is_muted = node_state.is_muted
            node.mixer_channel.is_solo = node_state.is_solo

            # Recreate and add plugins to the mixer channel
            for plugin_state in node_state.plugins:
                plugin_instance = self._deserialize_plugin(plugin_state)
                if plugin_instance:
                    # 将插件添加到轨道的混音通道
                    node.mixer_channel.add_insert(plugin_instance)
            return node

        elif isinstance(node_state, PluginState):
            # 如果插件作为独立的节点状态存在
            return self._deserialize_plugin(node_state)

        return None

    def _deserialize_plugin(self,
                            plugin_state: PluginState) -> Optional['IPlugin']:
        """Helper to deserialize a single plugin instance."""
        plugin_desc = self._registry.get_plugin_descriptor(
            plugin_state.unique_plugin_id)
        if plugin_desc:
            plugin_instance = self._node_factory.create_plugin_instance(
                plugin_desc)
            # Restore plugin state
            plugin_instance._node_id = plugin_state.instance_id
            plugin_instance.set_enabled(plugin_state.is_enabled)
            for name, p_state in plugin_state.parameters.items():
                if name in plugin_instance.get_parameters():
                    plugin_instance.get_parameters()[name]._set_value_internal(
                        p_state.value)
            return plugin_instance
        return None
