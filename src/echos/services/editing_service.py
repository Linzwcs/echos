from typing import Any, List, Dict
from ..agent.tools import tool
from ..interfaces import IDAWManager, IEditingService, ITrack
from ..models import ToolResponse, MIDIClip


class EditingService(IEditingService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    @tool(
        category="editing",
        description="Set a parameter value (volume, pan, etc.)",
        returns="Updated parameter value",
        examples=[
            "set_parameter_value(project_id='...', node_id='...', parameter_name='volume', value=-6.0)",
            "set_parameter_value(project_id='...', node_id='...', parameter_name='pan', value=0.5)"
        ])
    def set_parameter_value(
        self,
        project_id: str,
        node_id: str,
        parameter_name: str,
        value: Any,
    ) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node '{node_id}' not found.")

        params = {}
        if hasattr(node, 'get_parameters'):
            params = node.get_parameters()
        elif hasattr(node, 'mixer_channel') and hasattr(
                node.mixer_channel, 'get_parameters'):
            params = node.mixer_channel.get_parameters()

        parameter = params.get(parameter_name)
        if not parameter:
            return ToolResponse(
                "error", None,
                f"Parameter '{parameter_name}' not found on node '{node_id}'.")

        from echos.core.history.commands.editing_commands import SetParameterCommand
        command = SetParameterCommand(parameter, value)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "node_id": node_id,
                "parameter": parameter_name,
                "value": value
            }, command.description)
        return ToolResponse("error", None, command.error)

    @tool(category="editing",
          description="Add an automation point for a parameter",
          returns="Automation point information")
    def add_automation_point(
        self,
        project_id: str,
        node_id: str,
        parameter_name: str,
        beat: float,
        value: Any,
    ) -> ToolResponse:
        return ToolResponse(
            "error", None,
            "Add automation point not implemented via command yet.")

    @tool(
        category="editing",
        description="Create a MIDI clip on a track",
        returns="Created clip information",
        examples=[
            "create_midi_clip(project_id='...', track_id='...', start_beat=0.0, duration_beats=4.0, name='Piano Melody', clip_id=None)"
        ])
    def create_midi_clip(self,
                         project_id: str,
                         track_id: str,
                         start_beat: float,
                         duration_beats: float,
                         name: str = "MIDI Clip",
                         clip_id: str = None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node = project.router.nodes.get(track_id)
        from echos.interfaces import ITrack
        if not isinstance(node, ITrack):
            return ToolResponse("error", None,
                                f"Node '{track_id}' is not a valid track.")
        from echos.core.history.commands.editing_commands import CreateMidiClipCommand
        command = CreateMidiClipCommand(node,
                                        start_beat,
                                        duration_beats,
                                        name,
                                        clip_id=clip_id)
        project.command_manager.execute_command(command)
        if command.is_executed:
            clip = command._created_clip
            return ToolResponse("success", {
                "clip_id": clip.clip_id,
                "track_id": track_id
            }, command.description)
        print("herehereherehereherehere")
        return ToolResponse("error", None, command.error)

    @tool(category="editing",
          description="Add MIDI notes to a clip",
          returns="Number of notes added",
          examples=[
              '''add_notes_to_clip(
                project_id='...',
                clip_id='...',
                notes=[
                    {"pitch": 60, "velocity": 100, "start_beat": 0.0, "duration_beats": 1.0},
                    {"pitch": 64, "velocity": 100, "start_beat": 1.0, "duration_beats": 1.0}
                ]
            )'''
          ])
    def add_notes_to_clip(
        self,
        project_id: str,
        track_id: str,
        clip_id: str,
        notes: List[Dict[str, Any]],
    ) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        target_clip = None
        from echos.interfaces import ITrack
        track = project.router.nodes.get(track_id, None)
        if isinstance(track, ITrack):
            for clip in track.clips:
                if clip.clip_id == clip_id:
                    target_clip = clip
                    break

        if not target_clip:
            return ToolResponse("error", None, f"Clip '{clip_id}' not found.")

        from echos.models import MIDIClip, Note
        if not isinstance(target_clip, MIDIClip):
            return ToolResponse("error", None,
                                f"Clip '{clip_id}' is not a MIDI clip.")

        try:
            notes_to_add = []
            for n in notes:
                if isinstance(n, Note):
                    notes_to_add.append(n)
                elif isinstance(n, dict):
                    notes_to_add.append(Note(**n))
                else:
                    raise ValueError()

        except TypeError as e:
            return ToolResponse("error", None, f"Invalid note data: {e}")

        from echos.core.history.commands.editing_commands import AddNotesToClipCommand
        command = AddNotesToClipCommand(target_clip, notes_to_add)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "clip_id": clip_id,
                "notes_added": len(notes_to_add)
            }, command.description)
        return ToolResponse("error", None, command.error)

    @tool(
        category="editing",
        description="Remove a clip from a track.",
        returns="Confirmation of clip removal.",
        examples=[
            "editing.remove_clip(project_id='...', track_id='...', clip_id='...')"
        ])
    def remove_clip(self, project_id: str, track_id: str,
                    clip_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not isinstance(track, ITrack):
            return ToolResponse("error", None,
                                f"Track '{track_id}' not found.")
        from echos.core.history.commands.editing_commands import RemoveClipCommand
        command = RemoveClipCommand(track, clip_id)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "track_id": track_id,
                "removed_clip_id": clip_id
            }, command.description)
        return ToolResponse("error", None, command.error)

    @tool(
        category="editing",
        description="Remove MIDI notes from a clip by their unique IDs.",
        returns="Number of notes removed.",
        examples=[
            "editing.remove_notes_from_clip(project_id='...', track_id='...', clip_id='...', note_ids=['...', '...'])"
        ])
    def remove_notes_from_clip(self, project_id: str, track_id: str,
                               clip_id: str,
                               note_ids: List[str]) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        track = project.router.nodes.get(track_id)
        if not isinstance(track, ITrack):
            return ToolResponse("error", None,
                                f"Track '{track_id}' not found.")

        target_clip = next((c for c in track.clips if c.clip_id == clip_id),
                           None)
        if not target_clip:
            return ToolResponse(
                "error", None,
                f"Clip '{clip_id}' not found on track '{track_id}'.")

        if not isinstance(target_clip, MIDIClip):
            return ToolResponse("error", None,
                                f"Clip '{clip_id}' is not a MIDI clip.")

        notes_to_remove = [
            n for n in target_clip.notes if n.note_id in note_ids
        ]
        if len(notes_to_remove) != len(note_ids):
            found_ids = {n.note_id for n in notes_to_remove}
            missing_ids = [nid for nid in note_ids if nid not in found_ids]
            return ToolResponse(
                "error", None, f"Some notes not found in clip: {missing_ids}")

        from echos.core.history.commands.editing_commands import RemoveNotesFromClipCommand
        command = RemoveNotesFromClipCommand(target_clip, notes_to_remove)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "clip_id": clip_id,
                "notes_removed": len(notes_to_remove)
            }, command.description)
        return ToolResponse("error", None, command.error)
