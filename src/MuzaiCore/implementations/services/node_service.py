# file: src/MuzaiCore/implementations/services/node_service.py
from ...services.INodeService import INodeService
from ...services.api_types import ToolResponse, PluginIdentifier, NodeInfo
from ...interfaces import IDAWManager, IPluginRegistry, ITrack
from ...models.plugin_model import PluginCategory
from ...core.track import InstrumentTrack
from ...core.plugin import InstrumentPluginInstance, EffectPluginInstance


class NodeService(INodeService):

    def __init__(self, manager: IDAWManager, registry: IPluginRegistry):
        self._manager = manager
        self._registry = registry

    def create_instrument_track(self, project_id: str,
                                name: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found.")

        # TODO: This should use the Command pattern
        track = InstrumentTrack(name=name)
        project.add_node(track)

        return ToolResponse("success", {
            "node_id": track.node_id,
            "name": name,
            "type": "instrument_track"
        }, "Instrument track created.")

    def add_plugin_to_node(self, project_id: str, target_node_id: str,
                           plugin_unique_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found.")

        target_node = project.get_node_by_id(target_node_id)
        if not isinstance(target_node, ITrack):
            return ToolResponse(
                "error", None,
                f"Node {target_node_id} is not a track and cannot host plugins."
            )

        descriptor = self._registry.get_plugin_descriptor(plugin_unique_id)
        if not descriptor:
            return ToolResponse(
                "error", None,
                f"Plugin {plugin_unique_id} not found in registry.")

        # Instantiate the correct plugin type based on the descriptor
        if descriptor.category == PluginCategory.INSTRUMENT:
            plugin_instance = InstrumentPluginInstance(descriptor)
        elif descriptor.category == PluginCategory.EFFECT:
            plugin_instance = EffectPluginInstance(descriptor)
        else:
            return ToolResponse(
                "error", None,
                f"Plugin category '{descriptor.category}' not supported yet.")

        # TODO: This should be a command
        target_node.add_plugin(plugin_instance)

        return ToolResponse(
            "success", {"plugin_instance_id": plugin_instance.node_id},
            f"Plugin '{descriptor.name}' added to track '{target_node.name}'.")

    # (Other methods like list_nodes would be implemented here)
