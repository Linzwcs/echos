# file: src/MuzaiCore/services/transport_service.py
from ..interfaces import IDAWManager, ITransportService
from ..models import ToolResponse, TransportStatus
from ..core.history.commands.transport_command import SetTempoCommand, SetTimeSignatureCommand


class TransportService(ITransportService):
    """走带控制服务的具体实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def play(self, project_id: str) -> ToolResponse:
        """播放是瞬时引擎操作，不进入撤销栈。"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if project._audio_engine:
            project._audio_engine.play()
            # 注意：在真实应用中，状态应由引擎事件驱动更新
            project._transport_status = TransportStatus.PLAYING
            return ToolResponse("success", {"status": "playing"},
                                "Playback started.")
        return ToolResponse("error", None, "No audio engine attached.")

    def stop(self, project_id: str) -> ToolResponse:
        """停止也是瞬时引擎操作。"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if project._audio_engine:
            project._audio_engine.stop()
            project._transport_status = TransportStatus.STOPPED
            return ToolResponse("success", {"status": "stopped"},
                                "Playback stopped.")
        return ToolResponse("error", None, "No audio engine attached.")

    def set_tempo(self, project_id: str, bpm: float) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        command = SetTempoCommand(project.timeline, bpm)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {"tempo": bpm}, command.description)
        return ToolResponse("error", None, command.error)

    def set_time_signature(self, project_id: str, numerator: int,
                           denominator: int) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        command = SetTimeSignatureCommand(project.timeline, numerator,
                                          denominator)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "numerator": numerator,
                "denominator": denominator
            }, command.description)
        return ToolResponse("error", None, command.error)

    def get_transport_state(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        state = {
            "status": project.transport_status.value,
            "tempo": project.tempo,
            "time_signature": project.time_signature,
            "current_beat": project.current_beat
        }
        return ToolResponse("success", state, "Transport state retrieved.")

    def pause(self, project_id: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Pause is not implemented in mock engine.")
