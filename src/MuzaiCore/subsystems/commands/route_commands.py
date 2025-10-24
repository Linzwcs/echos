from typing import Any, List, Dict, Optional
from ...interfaces import ICommand, IProject, INode
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import PluginInstance
from ...models.clip_model import MIDIClip, Note


class CreateConnectionCommand(ICommand):
    """创建连接命令"""

    def __init__(self, project: IProject, source_port, dest_port):
        self._project = project
        self._source_port = source_port
        self._dest_port = dest_port
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            success = self._project.router.connect(self._source_port,
                                                   self._dest_port)
            if success:
                self._executed = True
                print(
                    f"✓ Connected: {self._source_port.owner_node_id[:8]}... → "
                    f"{self._dest_port.owner_node_id[:8]}...")
            return success
        except Exception as e:
            print(f"✗ Failed to create connection: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            self._project.router.disconnect(self._source_port.owner_node_id,
                                            self._dest_port.owner_node_id)
            self._executed = False
            print(
                f"✓ Undone: Disconnected {self._source_port.owner_node_id[:8]}... → "
                f"{self._dest_port.owner_node_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to undo connection: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        return f"Connect: {self._source_port.port_id} → {self._dest_port.port_id}"


class CreateSendCommand(ICommand):
    """创建发送命令"""

    def __init__(self,
                 project: IProject,
                 source_track_id: str,
                 dest_bus_id: str,
                 is_post_fader: bool = True):
        self._project = project
        self._source_track_id = source_track_id
        self._dest_bus_id = dest_bus_id
        self._is_post_fader = is_post_fader
        self._send = None  # 保存创建的send
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            source_track = self._project.get_node_by_id(self._source_track_id)
            if not hasattr(source_track, "mixer_channel"):
                return False

            self._send = source_track.mixer_channel.add_send(
                self._dest_bus_id, self._is_post_fader)
            self._executed = True
            print(f"✓ Created send: {self._source_track_id[:8]}... → "
                  f"{self._dest_bus_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to create send: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed or not self._send:
            return False
        try:
            source_track = self._project.get_node_by_id(self._source_track_id)
            if not hasattr(source_track, "mixer_channel"):
                return False

            source_track.mixer_channel.remove_send(self._send.send_id)
            self._executed = False
            print(f"✓ Undone: Removed send {self._send.send_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to undo send creation: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        send_type = "Post-fader" if self._is_post_fader else "Pre-fader"
        return f"Create {send_type} Send"
