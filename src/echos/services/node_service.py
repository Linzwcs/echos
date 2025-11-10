from typing import Optional
from ..agent.tools import tool
from ..interfaces import IDAWManager, INodeService
from ..models import ToolResponse
from ..core.history.commands.node_commands import CreateTrackCommand, RenameNodeCommand


class NodeService(INodeService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def _create_track(
        self,
        project_id: str,
        name: str,
        track_type: str,
        track_id: str = None,
    ) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node_factory = self._manager.node_factory
        command = CreateTrackCommand(router=project.router,
                                     node_factory=node_factory,
                                     track_type=track_type,
                                     name=name,
                                     track_id=track_id)
        project.command_manager.execute_command(command)

        if command.is_executed:
            track = command._created_track
            return ToolResponse(
                "success", {
                    "node_id": track.node_id,
                    "name": track.name,
                    "type": track.node_type
                }, command.description)
        return ToolResponse("error", None, command.error)

    @tool(category="node",
          description="Create an instrument track for MIDI instruments",
          returns="Created track information",
          examples=[
              "create_instrument_track(project_id='...', name='Piano')",
              "create_instrument_track(project_id='...', name='Synth Lead')"
          ])
    def create_instrument_track(self,
                                project_id: str,
                                name: str,
                                track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "InstrumentTrack",
                                  track_id=track_id)

    @tool(category="node",
          description="Create an audio track for audio recordings",
          returns="Created track information",
          examples=[
              "create_audio_track(project_id='...', name='Vocals')",
              "create_audio_track(project_id='...', name='Guitar')"
          ])
    def create_audio_track(self,
                           project_id: str,
                           name: str,
                           track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "AudioTrack",
                                  track_id=track_id)

    @tool(category="node",
          description="Create a bus track for grouping and effects",
          returns="Created track information",
          examples=[
              "create_bus_track(project_id='...', name='Reverb Bus')",
              "create_bus_track(project_id='...', name='Drum Bus')"
          ])
    def create_bus_track(self,
                         project_id: str,
                         name: str,
                         track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "BusTrack",
                                  track_id=track_id)

    @tool(category="node",
          description="Create a VCA track for volume control automation",
          returns="Created track information")
    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        nodes = project.router.nodes
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]

        data = [{
            "node_id": n.node_id,
            "name": n.name,
            "type": n.node_type
        } for n in nodes]
        return ToolResponse("success", {"nodes": data},
                            f"Found {len(data)} nodes.")

    def create_vca_track(self,
                         project_id: str,
                         name: str,
                         track_id: str = None) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    @tool(category="track",
          description="Delete a track from the project",
          returns="Deletion result")
    def delete_node(self, project_id: str, node_id: str) -> ToolResponse:

        return ToolResponse("error", None,
                            "Delete not implemented via service yet")

    @tool(category="track",
          description="Rename a track",
          returns="Renamed track information")
    def rename_node(self, project_id: str, node_id: str,
                    new_name: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Rename not implemented via service yet")

    @tool(category="plugin",
          description="Add a plugin to a track's effect chain",
          returns="Added plugin information")
    def add_insert_plugin(self,
                          project_id: str,
                          target_node_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None,
                          plugin_instance_id=None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        target_node = project.router.nodes.get(target_node_id)
        if not target_node:
            return ToolResponse(
                "error", None,
                f"Node '{target_node_id}' not found in project '{project_id}'."
            )

        try:
            descriptor = self._manager.plugin_registry.find_by_id(
                plugin_unique_id)
            plugin = self._manager.node_factory.create_plugin_instance(
                descriptor=descriptor, plugin_instance_id=plugin_instance_id)

            plugin_info = target_node.mixer_channel.add_insert(plugin, index)
            return ToolResponse(
                "success", plugin_info if plugin_info else {},
                f"Plugin '{plugin_unique_id}' added to node '{target_node_id}'."
            )
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to add plugin: {str(e)}")

    @tool(category="plugin",
          description="Remove a plugin from a track",
          returns="Removal result")
    def remove_insert_plugin(self, project_id: str, target_node_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Remove plugin not implemented via service yet")

    @tool(category="track",
          description="List all tracks in the project",
          returns="List of tracks with their information",
          examples=[
              "list_nodes(project_id='...')",
              "list_nodes(project_id='...', node_type='InstrumentTrack')"
          ])
    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        nodes = project.get_all_nodes()
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]

        data = [{
            "node_id": n.node_id,
            "name": n.name,
            "type": n.node_type
        } for n in nodes]

        return ToolResponse("success", {"nodes": data},
                            f"Found {len(data)} tracks.")
