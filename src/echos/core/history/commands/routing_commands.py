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


# --- (结束已有代码) ---


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
