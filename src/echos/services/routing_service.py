from ..agent.tools import tool
from ..interfaces import IDAWManager, IRoutingService, ITrack
from ..models import ToolResponse
from ..core.history.commands.routing_commands import CreateSendCommand


class RoutingService(IRoutingService):

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

    @tool(
        category="routing",
        description=
        "Connects the output port of one node to the input port of another.",
        returns="Confirmation of the connection.",
        examples=[
            "routing.connect(project_id='...', source_node_id='...', source_port_id='main_out', dest_node_id='...', dest_port_id='main_in')"
        ])
    def connect(self, project_id: str, source_node_id: str,
                source_port_id: str, dest_node_id: str,
                dest_port_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        from echos.core.history.commands import ConnectCommand
        command = ConnectCommand(router=project.router,
                                 source_node_id=source_node_id,
                                 source_port_id=source_port_id,
                                 dest_node_id=dest_node_id,
                                 dest_port_id=dest_port_id)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse(
                "success", {
                    "source": f"{source_node_id}:{source_port_id}",
                    "destination": f"{dest_node_id}:{dest_port_id}"
                }, command.description)
        return ToolResponse(
            "error", None, command.error
            or "Failed to execute connect command.")

    @tool(
        category="routing",
        description="Disconnects two previously connected nodes.",
        returns="Confirmation of the disconnection.",
        examples=[
            "routing.disconnect(project_id='...', source_node_id='...', source_port_id='main_out', dest_node_id='...', dest_port_id='main_in')"
        ])
    def disconnect(self, project_id: str, source_node_id: str,
                   source_port_id: str, dest_node_id: str,
                   dest_port_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        from echos.core.history.commands import DisconnectCommand
        command = DisconnectCommand(router=project.router,
                                    source_node_id=source_node_id,
                                    source_port_id=source_port_id,
                                    dest_node_id=dest_node_id,
                                    dest_port_id=dest_port_id)
        project.command_manager.execute_command(command)

        if command.is_executed:
            return ToolResponse(
                "success", {
                    "source": f"{source_node_id}:{source_port_id}",
                    "destination": f"{dest_node_id}:{dest_port_id}"
                }, command.description)
        return ToolResponse(
            "error", None, command.error
            or "Failed to execute disconnect command.")

    @tool(category="routing",
          description=
          "Lists all direct connections between nodes in the project.",
          returns="A list of all connections.")
    def list_connections(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        connections = project.router.get_all_connections()
        data = [{
            "source_node_id": c.source_node_id,
            "source_port_id": c.source_port_id,
            "dest_node_id": c.dest_node_id,
            "dest_port_id": c.dest_port_id,
        } for c in connections]
        return ToolResponse("success", {"connections": data},
                            f"Found {len(data)} connections.")
