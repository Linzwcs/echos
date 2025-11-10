from typing import Optional
from ....interfaces import IMixerChannel, IRouter
from ....models import Send, Port
from ..command_base import BaseCommand


class CreateSendCommand(BaseCommand):

    def __init__(self, mixer_channel: IMixerChannel, target_bus_id: str,
                 is_post_fader: bool):
        super().__init__(f"Create send to bus '{target_bus_id[:8]}...'")
        self._mixer_channel = mixer_channel
        self._target_bus_id = target_bus_id
        self._is_post_fader = is_post_fader
        self._created_send: Optional[Send] = None

    def _do_execute(self) -> bool:
        self._created_send = self._mixer_channel.add_send(
            target_bus_id=self._target_bus_id,
            is_post_fader=self._is_post_fader)
        return self._created_send is not None

    def _do_undo(self) -> bool:
        if self._created_send:
            return self._mixer_channel.remove_send(self._created_send.send_id)
        return False


class ConnectCommand(BaseCommand):
    """连接两个节点端口的命令。"""

    def __init__(self, router: IRouter, source_port: Port, dest_port: Port):
        super().__init__(
            f"Connect {source_port.owner_node_id[:6]}... to {dest_port.owner_node_id[:6]}..."
        )
        self._router = router
        self._source_port = source_port
        self._dest_port = dest_port

    def _do_execute(self) -> bool:
        return self._router.connect(self._source_port, self._dest_port)

    def _do_undo(self) -> bool:
        return self._router.disconnect(self._source_port, self._dest_port)


from typing import Optional
from ....interfaces import IMixerChannel, IRouter
from ....models import Send
from ..command_base import BaseCommand


class CreateSendCommand(BaseCommand):

    def __init__(self, mixer_channel: IMixerChannel, target_bus_id: str,
                 is_post_fader: bool):
        super().__init__(f"Create send to bus '{target_bus_id[:8]}...'")
        self._mixer_channel = mixer_channel
        self._target_bus_id = target_bus_id
        self._is_post_fader = is_post_fader
        self._created_send: Optional[Send] = None

    def _do_execute(self) -> bool:
        self._created_send = self._mixer_channel.add_send(
            target_bus_id=self._target_bus_id,
            is_post_fader=self._is_post_fader)
        return self._created_send is not None

    def _do_undo(self) -> bool:
        if self._created_send:
            return self._mixer_channel.remove_send(self._created_send.send_id)
        return False


class ConnectCommand(BaseCommand):

    def __init__(self, router: IRouter, source_node_id: str,
                 source_port_id: str, dest_node_id: str, dest_port_id: str):
        super().__init__(
            f"Connect {source_node_id[:6]}...:{source_port_id} to {dest_node_id[:6]}...:{dest_port_id}"
        )
        self._router = router
        self._source_node_id = source_node_id
        self._source_port_id = source_port_id
        self._dest_node_id = dest_node_id
        self._dest_port_id = dest_port_id

    def _do_execute(self) -> bool:
        result = self._router.connect(source_node_id=self._source_node_id,
                                      dest_node_id=self._dest_node_id,
                                      source_port_id=self._source_port_id,
                                      dest_port_id=self._dest_port_id)
        if not result:
            self._error = "Connection failed. Check if nodes/ports exist, types match, and no cycles are created."
        return result

    def _do_undo(self) -> bool:
        return self._router.disconnect(source_node_id=self._source_node_id,
                                       dest_node_id=self._dest_node_id,
                                       source_port_id=self._source_port_id,
                                       dest_port_id=self._dest_port_id)


class DisconnectCommand(BaseCommand):

    def __init__(self, router: IRouter, source_node_id: str,
                 source_port_id: str, dest_node_id: str, dest_port_id: str):
        super().__init__(
            f"Disconnect {source_node_id[:6]}:{source_port_id} from {dest_node_id[:6]}:{dest_port_id}"
        )
        self._router = router
        self._source_node_id = source_node_id
        self._source_port_id = source_port_id
        self._dest_node_id = dest_node_id
        self._dest_port_id = dest_port_id

    def _do_execute(self) -> bool:
        result = self._router.disconnect(source_node_id=self._source_node_id,
                                         dest_node_id=self._dest_node_id,
                                         source_port_id=self._source_port_id,
                                         dest_port_id=self._dest_port_id)
        if not result:
            self._error = "Disconnection failed. The connection may not have existed."
        return result

    def _do_undo(self) -> bool:
        return self._router.connect(source_node_id=self._source_node_id,
                                    dest_node_id=self._dest_node_id,
                                    source_port_id=self._source_port_id,
                                    dest_port_id=self._dest_port_id)
