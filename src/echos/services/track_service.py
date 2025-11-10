from typing import Optional, List, Dict, Any
from ..agent.tools import tool
from ..interfaces import IDAWManager, ITrackService, ITrack
from ..models import ToolResponse, MIDIClip, Note
from ..core.history.commands import (CreateTrackCommand, RenameNodeCommand,
                                     AddInsertPluginCommand,
                                     CreateMidiClipCommand,
                                     AddNotesToClipCommand)


class TrackService(ITrackService):

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

    @tool(
        category="track",
        description="Create an instrument track for MIDI instruments.",
        returns="Created track information.",
        examples=[
            "track.create_instrument_track(project_id='...', name='Piano')",
            "track.create_instrument_track(project_id='...', name='Synth Lead')"
        ])
    def create_instrument_track(self,
                                project_id: str,
                                name: str,
                                track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "InstrumentTrack",
                                  track_id=track_id)

    @tool(category="track",
          description="Create an audio track for audio recordings.",
          returns="Created track information.",
          examples=[
              "track.create_audio_track(project_id='...', name='Vocals')",
              "track.create_audio_track(project_id='...', name='Guitar')"
          ])
    def create_audio_track(self,
                           project_id: str,
                           name: str,
                           track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "AudioTrack",
                                  track_id=track_id)

    @tool(category="track",
          description="Create a bus track for grouping and effects.",
          returns="Created track information.",
          examples=[
              "track.create_bus_track(project_id='...', name='Reverb Bus')",
              "track.create_bus_track(project_id='...', name='Drum Bus')"
          ])
    def create_bus_track(self,
                         project_id: str,
                         name: str,
                         track_id: str = None) -> ToolResponse:
        return self._create_track(project_id,
                                  name,
                                  "BusTrack",
                                  track_id=track_id)

    @tool(
        category="track",
        description="List all tracks in the project.",
        returns="List of tracks with their information.",
        examples=[
            "track.list_tracks(project_id='...')",
            "track.list_tracks(project_id='...', node_type='InstrumentTrack')"
        ])
    def list_tracks(self,
                    project_id: str,
                    node_type: Optional[str] = None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        nodes = project.get_all_nodes()
        if node_type:
            nodes = [
                n for n in nodes
                if isinstance(n, ITrack) and n.node_type == node_type
            ]
        else:
            nodes = [n for n in nodes if isinstance(n, ITrack)]

        data = [{
            "node_id": n.node_id,
            "name": n.name,
            "type": n.node_type
        } for n in nodes]
        return ToolResponse("success", {"tracks": data},
                            f"Found {len(data)} tracks.")

    @tool(category="track",
          description="Delete a track from the project.",
          returns="Deletion result.")
    def delete_track(self, project_id: str, track_id: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Delete not implemented via service yet")

    @tool(category="track",
          description="Rename a track.",
          returns="Renamed track information.")
    def rename_track(self, project_id: str, track_id: str,
                     new_name: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Rename not implemented via service yet")

    @tool(category="track",
          description="Add a plugin to a track's effect chain.",
          returns="Added plugin information.")
    def add_insert_plugin(self,
                          project_id: str,
                          target_track_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None,
                          plugin_instance_id=None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        target_node = project.router.nodes.get(target_track_id)
        if not target_node:
            return ToolResponse(
                "error", None,
                f"Track '{target_track_id}' not found in project '{project_id}'."
            )

        try:
            descriptor = self._manager.plugin_registry.find_by_id(
                plugin_unique_id)
            if not descriptor:
                return ToolResponse("error", None,
                                    f"Plugin '{plugin_unique_id}' not found.")

            command = AddInsertPluginCommand(target_node,
                                             self._manager.node_factory,
                                             descriptor, index)
            project.command_manager.execute_command(command)

            if command.is_executed:
                return ToolResponse("success", {
                    "plugin_instance_id":
                    command._added_plugin.plugin_instance_id
                }, command.description)
            return ToolResponse("error", None, command.error)
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to add plugin: {str(e)}")

    @tool(category="track",
          description="Remove a plugin from a track.",
          returns="Removal result.")
    def remove_insert_plugin(self, project_id: str, target_track_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Remove plugin not implemented via service yet")
