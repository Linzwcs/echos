# file: src/MuzaiCore/services/routing_service.py
from ..interfaces import IDAWManager, IRoutingService, ITrack
from ..models import ToolResponse
from ..core.history.commands.routing_commands import CreateSendCommand


class RoutingService(IRoutingService):
    """路由服务的实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def create_send(self,
                    project_id: str,
                    source_track_id: str,
                    dest_bus_id: str,
                    is_post_fader: bool = True) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        source_node = project.get_node_by_id(source_track_id)
        dest_node = project.get_node_by_id(dest_bus_id)

        if not isinstance(source_node, ITrack) or not hasattr(
                source_node, 'mixer_channel'):
            return ToolResponse(
                "error", None,
                f"Source node '{source_track_id}' is not a valid track with a mixer channel."
            )
        if not (isinstance(dest_node, ITrack)
                and dest_node.node_type in ["BusTrack", "MasterTrack"]):
            return ToolResponse(
                "error", None,
                f"Destination node '{dest_bus_id}' is not a valid bus track.")

        mixer_channel = source_node.mixer_channel
        command = CreateSendCommand(mixer_channel, dest_bus_id, is_post_fader)
        project.command_manager.execute_command(command)

        if command.is_executed:
            send = command._created_send
            data = {
                "send_id": send.send_id,
                "source_track": source_track_id,
                "dest_bus": dest_bus_id,
                "post_fader": send.is_post_fader
            }
            return ToolResponse("success", data, command.description)
        return ToolResponse("error", None, command.error)

    # Connect/disconnect/list 涉及更底层的 Router 操作，它们通常也应该有对应的 Command
    def connect(self, project_id: str, source_node_id: str,
                source_port_id: str, dest_node_id: str,
                dest_port_id: str) -> ToolResponse:
        return ToolResponse("error", None,
                            "Direct connect not implemented via command yet.")

    def disconnect(self, project_id: str, source_node_id: str,
                   dest_node_id: str) -> ToolResponse:
        return ToolResponse(
            "error", None,
            "Direct disconnect not implemented via command yet.")

    def list_connections(self, project_id: str) -> ToolResponse:
        return ToolResponse("error", None, "List connections not implemented.")
