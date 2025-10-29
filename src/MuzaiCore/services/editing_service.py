from typing import Any, List, Dict
from ..interfaces.services import IEditingService
from ..interfaces.system import IDAWManager
from ..models import MIDIClip, Note, ToolResponse
from ..core.history.commands.all_commands import (
    CreateClipCommand,
    AddNotesToClipCommand,
)
import uuid


class EditingService(IEditingService):
    """
    重构后的编辑服务（Command驱动）
    """

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def set_parameter_value(self, project_id: str, node_id: str,
                            parameter_name: str, value: Any) -> ToolResponse:
        """
        设置参数值（已经是Command驱动，保持不变）
        
        这个方法已经正确使用了Command！
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        parameters = node.get_parameters()
        if parameter_name not in parameters:
            return ToolResponse("error", None,
                                f"Parameter '{parameter_name}' not found")

        param = parameters[parameter_name]

        command = param.create_set_value_command(value)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "node_id": node_id,
                "parameter": parameter_name,
                "value": value
            }, f"Parameter '{parameter_name}' set to {value} (undoable)")

    def add_automation_point(self, project_id: str, node_id: str,
                             parameter_name: str, beat: float,
                             value: Any) -> ToolResponse:
        """
        添加自动化点（需要改为Command驱动）
        
        当前问题：
            param.add_automation_point(beat, value)  # ✗ 直接操作
        
        应该改为：
            command = AddAutomationPointCommand(...)
            project.command_manager.execute_command(command)
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        parameters = node.get_parameters()
        if parameter_name not in parameters:
            return ToolResponse("error", None,
                                f"Parameter '{parameter_name}' not found")

        param = parameters[parameter_name]

        # 导入AddAutomationPointCommand（需要在all_commands.py中实现）
        from ..subsystems.commands.parameter_commands import AddAutomationPointCommand

        command = AddAutomationPointCommand(param, beat, value)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "node_id": node_id,
                "parameter": parameter_name,
                "beat": beat,
                "value": value
            }, f"Automation point added at beat {beat} (undoable)")

    def create_midi_clip(self,
                         project_id: str,
                         track_id: str,
                         start_beat: float,
                         duration_beats: float,
                         name: str = "MIDI Clip") -> ToolResponse:
        """
        创建MIDI片段（改为Command驱动）
        
        旧方式：
            clip = MIDIClip(...)
            track.add_clip(clip)  # ✗ 直接操作
        
        新方式：
            clip = MIDIClip(...)
            command = CreateClipCommand(...)
            command_manager.execute_command(command)
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        track = project.get_node_by_id(track_id)
        if not hasattr(track, "add_clip"):
            return ToolResponse("error", None,
                                f"Node {track_id} cannot host clips")

        # 创建clip对象
        clip = MIDIClip(clip_id=str(uuid.uuid4()),
                        start_beat=start_beat,
                        duration_beats=duration_beats,
                        name=name)

        # 创建并执行Command
        command = CreateClipCommand(project, track_id, clip)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "clip_id": clip.clip_id,
                "track_id": track_id,
                "start_beat": start_beat,
                "duration_beats": duration_beats
            }, f"MIDI clip '{name}' created (undoable)")

    def add_notes_to_clip(self, project_id: str, clip_id: str,
                          notes: List[Dict[str, Any]]) -> ToolResponse:
        """
        添加音符到片段（改为Command驱动）
        
        支持Command合并：
        - 连续添加音符会合并成单个撤销步骤
        - Agent可以"尝试"添加音符，不满意就撤销
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        # 转换为Note对象
        note_objects = [
            Note(pitch=note_data["pitch"],
                 velocity=note_data["velocity"],
                 start_beat=note_data["start_beat"],
                 duration_beats=note_data["duration_beats"])
            for note_data in notes
        ]

        # 创建并执行Command
        command = AddNotesToClipCommand(project, clip_id, note_objects)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {
            "clip_id": clip_id,
            "notes_added": len(notes)
        }, f"{len(notes)} notes added to clip (undoable)")
