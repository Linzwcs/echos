# file: src/MuzaiCore/implementations/services/transport_service.py
from ..interfaces.services import ITransportService
from ..models import ToolResponse, TransportStatus
from ..interfaces import IDAWManager

from ..core.history.commands.transport_commands import SetTempoCommand, SetTimeSignatureCommand


class TransportService(ITransportService):
    """
    走带控制服务
    
    操作分类：
    - 修改项目状态（tempo, time_signature）→ Command
    - 瞬态控制（play, stop, pause）→ 直接调用
    - 查询（get_transport_state）→ 直接访问
    """

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def play(self, project_id: str) -> ToolResponse:
        """
        开始播放（瞬态操作，不需要Command）
        
        原因：
        - 不修改项目状态（只是运行引擎）
        - 不需要撤销（可以直接stop）
        - 实时性要求高
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if hasattr(project, 'engine') and project.engine:
            project.engine.play()
            return ToolResponse("success", {"status": "playing"},
                                "Playback started")
        else:
            return ToolResponse("error", None, "No audio engine available")

    def stop(self, project_id: str) -> ToolResponse:
        """停止播放（瞬态操作，不需要Command）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if hasattr(project, 'engine') and project.engine:
            project.engine.stop()
            return ToolResponse("success", {"status": "stopped"},
                                "Playback stopped")
        else:
            return ToolResponse("error", None, "No audio engine available")

    def pause(self, project_id: str) -> ToolResponse:
        """暂停播放（瞬态操作，不需要Command）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        project.set_transport_status(TransportStatus.PAUSED)
        return ToolResponse("success", {"status": "paused"}, "Playback paused")

    def set_tempo(self, project_id: str, bpm: float) -> ToolResponse:
        """
        设置速度（使用Command - 可撤销）
        
        这是项目状态的修改，需要Command：
        - 修改project.tempo
        - 需要撤销
        - 支持Command合并（连续调整速度）
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if bpm <= 0 or bpm > 999:
            return ToolResponse("error", None,
                                "Tempo must be between 1 and 999 BPM")

        # 创建并执行Command
        command = SetTempoCommand(project, bpm)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {"tempo": bpm},
                            f"Tempo set to {bpm} BPM (undoable)")

    def set_time_signature(self, project_id: str, numerator: int,
                           denominator: int) -> ToolResponse:
        """
        设置拍号（使用Command - 可撤销）
        
        这是项目状态的修改，需要Command
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        if numerator <= 0 or denominator <= 0:
            return ToolResponse("error", None, "Invalid time signature")

        if denominator not in [2, 4, 8, 16]:
            return ToolResponse("error", None,
                                "Denominator must be 2, 4, 8, or 16")

        # 创建并执行Command
        command = SetTimeSignatureCommand(project, numerator, denominator)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "numerator": numerator,
                "denominator": denominator
            }, f"Time signature set to {numerator}/{denominator} (undoable)")

    def get_transport_state(self, project_id: str) -> ToolResponse:
        """获取走带状态（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        return ToolResponse(
            "success", {
                "status": project.transport_status.value,
                "tempo": project.tempo,
                "time_signature": {
                    "numerator": project.time_signature[0],
                    "denominator": project.time_signature[1]
                }
            }, "Transport state retrieved")
