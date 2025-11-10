from abc import abstractmethod
from echos.models import ToolResponse
from .ibase_service import IService


class ITransportService(IService):

    @abstractmethod
    def play(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def stop(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def pause(self, project_id: str) -> ToolResponse:
        pass

    @abstractmethod
    def set_tempo(self, project_id: str, bpm: float) -> ToolResponse:
        pass

    @abstractmethod
    def set_time_signature(
        self,
        project_id: str,
        numerator: int,
        denominator: int,
    ) -> ToolResponse:
        pass

    @abstractmethod
    def get_transport_state(self, project_id: str) -> ToolResponse:
        pass
