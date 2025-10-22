# file: src/MuzaiCore/implementations/services/transport_service.py
from ...services.ITransportService import ITransportService
from ...services.api_types import ToolResponse
from ...interfaces import IDAWManager


class TransportService(ITransportService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def play(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found.")

        project.engine.play()
        return ToolResponse("success", {"status": "playing"},
                            "Playback started.")

    def stop(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found.")

        project.engine.stop()
        return ToolResponse("success", {"status": "stopped"},
                            "Playback stopped.")

    def set_tempo(self, project_id: str, bpm: float) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found.")

        # TODO: This should be a command
        project.tempo = bpm
        project.timeline.set_tempo(bpm)

        return ToolResponse("success", {"tempo": bpm},
                            f"Tempo set to {bpm} BPM.")
