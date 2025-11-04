# file: src/MuzaiCore/core/history/commands/node_commands.py
from typing import Optional, List
from ....interfaces import IRouter, INode, ITrack, IPlugin, IProject
from ....interfaces.system.ifactory import INodeFactory
from ....models import Connection, PluginDescriptor
from ..command_base import BaseCommand


# --- (已有 CreateTrackCommand 和 RenameNodeCommand) ---
class CreateTrackCommand(BaseCommand):
    """创建一个新轨道的命令。"""

    def __init__(self, router: IRouter, node_factory: INodeFactory,
                 track_type: str, name: str):
        super().__init__(f"Create {track_type} '{name}'")
        self._router = router
        self._node_factory = node_factory
        self._track_type = track_type
        self._name = name
        self._created_track: Optional[ITrack] = None

    def _do_execute(self) -> bool:
        if self._track_type == "InstrumentTrack":
            self._created_track = self._node_factory.create_instrument_track(
                self._name)
        elif self._track_type == "AudioTrack":
            self._created_track = self._node_factory.create_audio_track(
                self._name)
        elif self._track_type == "BusTrack":
            self._created_track = self._node_factory.create_bus_track(
                self._name)
        else:
            self._error = f"Unknown track type: {self._track_type}"
            return False
        self._router.add_node(self._created_track)
        return True

    def _do_undo(self) -> bool:
        if self._created_track:
            self._router.remove_node(self._created_track.node_id)
            return True
        return False


class RenameNodeCommand(BaseCommand):
    """重命名节点的命令。"""

    def __init__(self, node: INode, new_name: str):
        self._node = node
        self._old_name = node.name
        self._new_name = new_name
        super().__init__(f"Rename '{self._old_name}' to '{self._new_name}'")

    def _do_execute(self) -> bool:
        self._node.name = self._new_name
        return True

    def _do_undo(self) -> bool:
        self._node.name = self._old_name
        return True


class DeleteNodeCommand(BaseCommand):
    """删除一个节点的命令。"""

    def __init__(self, project: IProject, node_id: str):
        self._project = project
        self._router = project.router
        self._node_id = node_id
        self._deleted_node: Optional[INode] = None
        self._connections: List[Connection] = []
        node_to_delete = self._router.get_node_by_id(node_id)
        super().__init__(
            f"Delete Node '{node_to_delete.name if node_to_delete else node_id}'"
        )

    def _do_execute(self) -> bool:
        self._deleted_node = self._router.get_node_by_id(self._node_id)
        if not self._deleted_node:
            self._error = f"Node '{self._node_id}' not found for deletion."
            return False

        # 保存与该节点相关的连接，以便撤销
        self._connections.extend(
            self._router.get_inputs_for_node(self._node_id))
        self._connections.extend(
            self._router.get_outputs_for_node(self._node_id))

        self._router.remove_node(self._node_id)
        return True

    def _do_undo(self) -> bool:
        if self._deleted_node:
            self._router.add_node(self._deleted_node)
            # 重新建立连接
            for conn in self._connections:
                self._router.connect(conn.source_port, conn.dest_port)
            return True
        return False


class AddInsertPluginCommand(BaseCommand):
    """向轨道添加插件的命令。"""

    def __init__(self, track: ITrack, node_factory: INodeFactory,
                 plugin_descriptor: PluginDescriptor, index: Optional[int]):
        super().__init__(
            f"Add Plugin '{plugin_descriptor.name}' to '{track.name}'")
        self._track = track
        self._node_factory = node_factory
        self._plugin_descriptor = plugin_descriptor
        self._index = index
        self._added_plugin: Optional[IPlugin] = None

    def _do_execute(self) -> bool:
        if not hasattr(self._track, 'mixer_channel'):
            self._error = f"Track '{self._track.name}' has no mixer channel."
            return False

        self._added_plugin = self._node_factory.create_plugin_instance(
            self._plugin_descriptor, self._track.event_bus)
        self._track.mixer_channel.add_insert(self._added_plugin, self._index)
        return True

    def _do_undo(self) -> bool:
        if self._added_plugin and hasattr(self._track, 'mixer_channel'):
            return self._track.mixer_channel.remove_insert(
                self._added_plugin.node_id)
        return False


class RemoveInsertPluginCommand(BaseCommand):
    """从轨道移除插件的命令。"""

    def __init__(self, track: ITrack, plugin_instance_id: str):
        self._track = track
        self._plugin_instance_id = plugin_instance_id
        self._removed_plugin: Optional[IPlugin] = None
        self._removed_index: Optional[int] = None

        plugin = next((p for p in track.mixer_channel.inserts
                       if p.node_id == plugin_instance_id), None)
        super().__init__(
            f"Remove Plugin '{plugin.descriptor.name if plugin else plugin_instance_id}' from '{track.name}'"
        )

    def _do_execute(self) -> bool:
        if not hasattr(self._track, 'mixer_channel'):
            self._error = f"Track '{self._track.name}' has no mixer channel."
            return False

        mixer = self._track.mixer_channel
        for i, plugin in enumerate(mixer.inserts):
            if plugin.node_id == self._plugin_instance_id:
                self._removed_index = i
                self._removed_plugin = plugin
                break

        if self._removed_plugin:
            return mixer.remove_insert(self._plugin_instance_id)

        self._error = f"Plugin instance '{self._plugin_instance_id}' not found."
        return False

    def _do_undo(self) -> bool:
        if self._removed_plugin and self._removed_index is not None and hasattr(
                self._track, 'mixer_channel'):
            self._track.mixer_channel.add_insert(self._removed_plugin,
                                                 self._removed_index)
            return True
        return False
