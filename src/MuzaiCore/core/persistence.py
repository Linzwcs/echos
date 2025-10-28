# file: src/MuzaiCore/persistence/project_serializer.py
from ..interfaces.system.iproject import IProject
from ..interfaces.system.inode_factory import INodeFactory
from ..interfaces.system.ipersistence import IProjectSerializer
from ..models import ProjectState, TrackState, PluginState, ParameterState
from ..core.domain.project import Project
from ..core.history.command_manager import CommandManager
from ..core.timeline import Timeline


class ProjectSerializer(IProjectSerializer):
    """
    Handles the conversion between live Project objects and serializable
    ProjectState DTOs.
    """

    def __init__(self, node_factory: INodeFactory):
        # The factory is crucial for deserialization, as it knows how to create
        # the correct backend-specific node instances.
        self._node_factory = node_factory

    def serialize(self, project: IProject) -> ProjectState:
        """Converts a live Project object into a ProjectState DTO."""
        nodes_state = {}
        for node in project.get_all_nodes():
            nodes_state[node.node_id] = self._serialize_node(node)

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

        # 1. Create the basic project structure
        new_project = Project(
            name=state.name,
            project_id=state.project_id,
            command_manager=CommandManager(),
            timeline=Timeline(state.tempo, (state.time_signature_numerator,
                                            state.time_signature_denominator)))

        # 2. Recreate all nodes using the factory
        for node_id, node_state in state.nodes.items():
            recreated_node = self._deserialize_node(node_state)
            if recreated_node:
                new_project.add_node(recreated_node)

        # 3. Re-establish all routing connections
        for connection in state.routing_graph:
            new_project.router.connect(connection.source_port,
                                       connection.dest_port)

        return new_project

    def _serialize_node(self, node: 'INode') -> 'NodeState':
        """Helper to serialize a single node."""
        from ..core.domain.track import ITrack
        if isinstance(node, ITrack):
            plugins = [
                self._serialize_plugin(p) for p in node.mixer_channel.inserts
            ]
            return TrackState(
                node_id=node.node_id,
                name=node.name,
                track_type=type(node).__name__,
                clips=list(node.clips),  # Assumes clips are dataclasses
                plugins=plugins,
                volume=ParameterState(name="volume",
                                      value=node.mixer_channel.volume.value),
                pan=ParameterState(name="pan",
                                   value=node.mixer_channel.pan.value),
                is_muted=node.mixer_channel.is_muted,
                is_solo=node.mixer_channel.is_solo,
            )
        # Add logic for other node types if they exist
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
            # Use the factory to create the correct track type
            track_type_name = node_state.track_type.lower()
            if "instrument" in track_type_name:
                node = self._node_factory.create_instrument_track(
                    node_state.name)
            elif "audio" in track_type_name:
                node = self._node_factory.create_audio_track(node_state.name)
            # ... etc. for Bus, VCA

            # Restore state
            node._node_id = node_state.node_id  # Override generated ID
            node.clips = node_state.clips
            node.mixer_channel.volume._set_value_internal(
                node_state.volume.value)
            node.mixer_channel.pan._set_value_internal(node_state.pan.value)

            # Recreate and add plugins
            for plugin_state in node_state.plugins:
                plugin_desc = self._registry.get_plugin_descriptor(
                    plugin_state.unique_plugin_id)
                if plugin_desc:
                    plugin_instance = self._node_factory.create_plugin_instance(
                        plugin_desc)
                    # Restore plugin state
                    plugin_instance._node_id = plugin_state.instance_id
                    for name, p_state in plugin_state.parameters.items():
                        plugin_instance.get_parameters(
                        )[name]._set_value_internal(p_state.value)
                    node.mixer_channel.add_insert(plugin_instance)
            return node
        return None
