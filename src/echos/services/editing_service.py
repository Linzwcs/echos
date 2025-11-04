# file: src/MuzaiCore/services/editing_service.py
from typing import Any, List, Dict
from ..interfaces import IDAWManager, IEditingService, ITrack
from ..models import ToolResponse, Note, MIDIClip
from ..core.history.commands.editing_commands import (SetParameterCommand,
                                                      CreateMidiClipCommand,
                                                      AddNotesToClipCommand)


class EditingService(IEditingService):
    """编辑服务的实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def set_parameter_value(self, project_id: str, node_id: str,
                            parameter_name: str, value: Any) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node '{node_id}' not found.")

        # 参数可能在节点自身（如轨道），也可能在混音通道上
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

        command = SetParameterCommand(parameter, value)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "node_id": node_id,
                "parameter": parameter_name,
                "value": value
            }, command.description)
        return ToolResponse("error", None, command.error)

    def create_midi_clip(self,
                         project_id: str,
                         track_id: str,
                         start_beat: float,
                         duration_beats: float,
                         name: str = "MIDI Clip") -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node = project.get_node_by_id(track_id)
        if not isinstance(node, ITrack):
            return ToolResponse("error", None,
                                f"Node '{track_id}' is not a valid track.")

        command = CreateMidiClipCommand(node, start_beat, duration_beats, name)
        project.command_manager.execute_command(command)

        if command.is_executed:
            clip = command._created_clip
            return ToolResponse("success", {
                "clip_id": clip.clip_id,
                "track_id": track_id
            }, command.description)
        return ToolResponse("error", None, command.error)

    def add_notes_to_clip(self, project_id: str, clip_id: str,
                          notes: List[Dict[str, Any]]) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        # 找到包含该 clip_id 的轨道和 clip 对象
        target_clip = None
        owner_track = None
        for track in project.get_all_nodes():
            if isinstance(track, ITrack):
                for clip in track.clips:
                    if clip.clip_id == clip_id:
                        target_clip = clip
                        owner_track = track
                        break
            if target_clip:
                break

        if not target_clip:
            return ToolResponse("error", None,
                                f"Clip '{clip_id}' not found in the project.")
        if not isinstance(target_clip, MIDIClip):
            return ToolResponse("error", None,
                                f"Clip '{clip_id}' is not a MIDI clip.")

        try:
            notes_to_add = [Note(**n) for n in notes]
        except TypeError as e:
            return ToolResponse("error", None,
                                f"Invalid note data provided: {e}")

        command = AddNotesToClipCommand(target_clip, notes_to_add)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "clip_id": clip_id,
                "notes_added": len(notes_to_add)
            }, command.description)
        return ToolResponse("error", None, command.error)

    def add_automation_point(self, project_id: str, node_id: str,
                             parameter_name: str, beat: float,
                             value: Any) -> ToolResponse:
        # 自动化点的添加也可以通过一个 Command 来实现，以支持撤销
        # 这里暂时作为直接操作，留作练习
        return ToolResponse(
            "error", None,
            "Add automation point is not implemented via command yet.")
