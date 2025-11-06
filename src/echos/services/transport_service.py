from ..agent.tools import tool
from ..interfaces import IDAWManager, ITransportService
from ..models import ToolResponse, TransportStatus
from ..core.history.commands.transport_command import SetTempoCommand, SetTimeSignatureCommand


class TransportService(ITransportService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    @tool(category="transport",
          description="Start playback",
          returns="Playback status",
          examples=["play(project_id='...')"])
    def play(self, project_id: str) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if project._audio_engine:
            project._audio_engine.play()
            from echos.models import TransportStatus
            project._transport_status = TransportStatus.PLAYING
            return ToolResponse("success", {"status": "playing"},
                                "Playback started.")
        return ToolResponse("error", None, "No audio engine attached.")

    @tool(category="transport",
          description="Stop playback",
          returns="Playback status")
    def stop(self, project_id: str) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        if project._audio_engine:
            project._audio_engine.stop()
            from echos.models import TransportStatus
            project._transport_status = TransportStatus.STOPPED
            return ToolResponse("success", {"status": "stopped"},
                                "Playback stopped.")
        return ToolResponse("error", None, "No audio engine attached.")

    @tool(category="transport",
          description="Pause playback",
          returns="Playback status")
    def pause(self, project_id: str) -> ToolResponse:

        return ToolResponse("error", None, "Pause not implemented in engine.")

    @tool(category="transport",
          description="Set project tempo in BPM",
          returns="Updated tempo",
          examples=[
              "set_tempo(project_id='...', bpm=120.0)",
              "set_tempo(project_id='...', bpm=140.0)"
          ])
    def set_tempo(self, project_id: str, beat: float,
                  bpm: float) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        from echos.core.history.commands.transport_command import SetTempoCommand
        command = SetTempoCommand(project.timeline, beat, bpm)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {"tempo": bpm}, command.description)
        return ToolResponse("error", None, command.error)

    @tool(
        category="transport",
        description="Set project time signature",
        returns="Updated time signature",
        examples=[
            "set_time_signature(project_id='...', numerator=4, denominator=4)",
            "set_time_signature(project_id='...', numerator=3, denominator=4)"
        ])
    def set_time_signature(self, project_id: str, beat: float, numerator: int,
                           denominator: int) -> ToolResponse:

        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        from echos.core.history.commands.transport_command import SetTimeSignatureCommand
        command = SetTimeSignatureCommand(project.timeline, beat, numerator,
                                          denominator)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse("success", {
                "numerator": numerator,
                "denominator": denominator
            }, command.description)
        return ToolResponse("error", None, command.error)

    @tool(
        category="transport",
        description="Get current transport state",
        returns=
        "Transport state including tempo, time signature, and playback status")
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
