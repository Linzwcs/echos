# file: src/MuzaiCore/subsystems/commands/all_commands.py
"""
完整的Command系统 - 覆盖所有可撤销操作
每个Service方法都应该对应一个Command
"""
from typing import Any, List, Dict, Optional
from ....interfaces.system import ICommand, IProject, INode
from ....core.track import InstrumentTrack, AudioTrack, BusTrack
from ....core.plugin import Plugin
from ....models.clip_model import MIDIClip, Note


class CreateNodeCommand(ICommand):
    """通用的创建节点命令"""

    def __init__(self, project: IProject, node: INode):
        self._project = project
        self._node = node
        self._node_id = node.node_id
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            self._project.add_node(self._node)
            self._project.router.add_node(self._node)
            self._executed = True
            print(f"✓ Created node: {self._node_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to create node: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            self._project.router.remove_node(self._node_id)
            self._project.remove_node(self._node_id)
            self._executed = False
            print(f"✓ Undone: Removed node {self._node_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to undo node creation: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        node_type = type(self._node).__name__
        node_name = getattr(self._node, "name", "Unknown")
        return f"Create {node_type}: '{node_name}'"


class DeleteNodeCommand(ICommand):
    """删除节点命令"""

    def __init__(self, project: IProject, node_id: str):
        self._project = project
        self._node_id = node_id
        self._node = None  # 保存删除的节点用于撤销
        self._connections = []  # 保存删除的连接
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            # 保存节点引用
            self._node = self._project.get_node_by_id(self._node_id)
            if not self._node:
                return False

            # 保存所有相关连接
            self._connections = [
                *self._project.router.get_inputs_for_node(self._node_id),
                *self._project.router.get_outputs_for_node(self._node_id)
            ]

            # 执行删除
            self._project.router.remove_node(self._node_id)
            self._project.remove_node(self._node_id)
            self._executed = True
            print(f"✓ Deleted node: {self._node_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to delete node: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed or not self._node:
            return False
        try:
            # 恢复节点
            self._project.add_node(self._node)
            self._project.router.add_node(self._node)

            # 恢复连接
            for conn in self._connections:
                self._project.router.connect(conn.source_port, conn.dest_port)

            self._executed = False
            print(f"✓ Undone: Restored node {self._node_id[:8]}...")
            return True
        except Exception as e:
            print(f"✗ Failed to undo node deletion: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        node_name = getattr(self._node, "name",
                            "Unknown") if self._node else "Unknown"
        return f"Delete Node: '{node_name}'"


class RenameNodeCommand(ICommand):
    """重命名节点命令"""

    def __init__(self, project: IProject, node_id: str, new_name: str):
        self._project = project
        self._node_id = node_id
        self._new_name = new_name
        self._old_name = None
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            node = self._project.get_node_by_id(self._node_id)
            if not node:
                return False

            self._old_name = getattr(node, "name", "Unknown")
            setattr(node, "name", self._new_name)
            self._executed = True
            print(f"✓ Renamed: '{self._old_name}' → '{self._new_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to rename node: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            node = self._project.get_node_by_id(self._node_id)
            if not node:
                return False

            setattr(node, "name", self._old_name)
            self._executed = False
            print(f"✓ Undone: '{self._new_name}' → '{self._old_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to undo rename: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        # 可以合并连续的重命名操作
        return (isinstance(other, RenameNodeCommand)
                and self._node_id == other._node_id and self._executed
                and not other._executed)

    def merge_with(self, other: ICommand):
        if not self.can_merge_with(other):
            raise ValueError("Cannot merge commands")
        # 保留最初的old_name，更新为最新的new_name
        self._new_name = other._new_name

    @property
    def description(self) -> str:
        return f"Rename: '{self._old_name}' → '{self._new_name}'"


# ============================================================================
# 2. 插件管理Commands
# ============================================================================


class AddInsertPluginCommand(ICommand):
    """添加插入效果命令"""

    def __init__(self,
                 project: IProject,
                 target_node_id: str,
                 plugin_instance: Plugin,
                 index: Optional[int] = None):
        self._project = project
        self._target_node_id = target_node_id
        self._plugin_instance = plugin_instance
        self._index = index
        self._actual_index = None  # 实际插入的位置
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            node = self._project.get_node_by_id(self._target_node_id)
            if not hasattr(node, "mixer_channel"):
                return False

            # 记录实际插入位置
            if self._index is None:
                self._actual_index = len(node.mixer_channel.inserts)
            else:
                self._actual_index = self._index

            node.mixer_channel.add_insert(self._plugin_instance, self._index)
            self._executed = True
            print(f"✓ Added plugin: {self._plugin_instance.descriptor.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to add plugin: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            node = self._project.get_node_by_id(self._target_node_id)
            if not hasattr(node, "mixer_channel"):
                return False

            node.mixer_channel.remove_insert(self._plugin_instance.node_id)
            self._executed = False
            print(
                f"✓ Undone: Removed plugin {self._plugin_instance.descriptor.name}"
            )
            return True
        except Exception as e:
            print(f"✗ Failed to undo plugin addition: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        return f"Add Plugin: '{self._plugin_instance.descriptor.name}'"


class RemoveInsertPluginCommand(ICommand):
    """移除插入效果命令"""

    def __init__(self, project: IProject, target_node_id: str,
                 plugin_instance_id: str):
        self._project = project
        self._target_node_id = target_node_id
        self._plugin_instance_id = plugin_instance_id
        self._plugin_instance = None  # 保存用于撤销
        self._index = None  # 保存原始位置
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            node = self._project.get_node_by_id(self._target_node_id)
            if not hasattr(node, "mixer_channel"):
                return False

            # 保存插件和位置
            for i, plugin in enumerate(node.mixer_channel.inserts):
                if plugin.node_id == self._plugin_instance_id:
                    self._plugin_instance = plugin
                    self._index = i
                    break

            if not self._plugin_instance:
                return False

            node.mixer_channel.remove_insert(self._plugin_instance_id)
            self._executed = True
            print(f"✓ Removed plugin: {self._plugin_instance.descriptor.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to remove plugin: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed or not self._plugin_instance:
            return False
        try:
            node = self._project.get_node_by_id(self._target_node_id)
            if not hasattr(node, "mixer_channel"):
                return False

            node.mixer_channel.add_insert(self._plugin_instance, self._index)
            self._executed = False
            print(
                f"✓ Undone: Restored plugin {self._plugin_instance.descriptor.name}"
            )
            return True
        except Exception as e:
            print(f"✗ Failed to undo plugin removal: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        plugin_name = (self._plugin_instance.descriptor.name
                       if self._plugin_instance else "Unknown")
        return f"Remove Plugin: '{plugin_name}'"


# ============================================================================
# 3. 路由Commands
# ============================================================================


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


# ============================================================================
# 4. Clip和Note Commands
# ============================================================================


class CreateClipCommand(ICommand):
    """创建片段命令"""

    def __init__(self, project: IProject, track_id: str, clip: MIDIClip):
        self._project = project
        self._track_id = track_id
        self._clip = clip
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            track = self._project.get_node_by_id(self._track_id)
            if not hasattr(track, "add_clip"):
                return False

            track.add_clip(self._clip)
            self._executed = True
            print(f"✓ Created clip: {self._clip.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to create clip: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            track = self._project.get_node_by_id(self._track_id)
            if not hasattr(track, "remove_clip"):
                return False

            track.remove_clip(self._clip.clip_id)
            self._executed = False
            print(f"✓ Undone: Removed clip {self._clip.name}")
            return True
        except Exception as e:
            print(f"✗ Failed to undo clip creation: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        return f"Create Clip: '{self._clip.name}'"


class AddNotesToClipCommand(ICommand):
    """添加音符到片段命令"""

    def __init__(self, project: IProject, clip_id: str, notes: List[Note]):
        self._project = project
        self._clip_id = clip_id
        self._notes = notes
        self._clip = None  # 保存clip引用
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            # 查找clip
            for node in self._project.get_all_nodes():
                if hasattr(node, "clips"):
                    for clip in node.clips:
                        if clip.clip_id == self._clip_id:
                            self._clip = clip
                            break

            if not self._clip:
                return False

            # 添加音符
            for note in self._notes:
                self._clip.notes.add(note)

            self._executed = True
            print(f"✓ Added {len(self._notes)} notes to clip")
            return True
        except Exception as e:
            print(f"✗ Failed to add notes: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed or not self._clip:
            return False
        try:
            # 移除音符
            for note in self._notes:
                self._clip.notes.discard(note)

            self._executed = False
            print(f"✓ Undone: Removed {len(self._notes)} notes from clip")
            return True
        except Exception as e:
            print(f"✗ Failed to undo note addition: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        # 可以合并对同一个clip的音符添加
        return (isinstance(other, AddNotesToClipCommand)
                and self._clip_id == other._clip_id and self._executed
                and not other._executed)

    def merge_with(self, other: ICommand):
        if not self.can_merge_with(other):
            raise ValueError("Cannot merge commands")
        # 合并音符列表
        self._notes.extend(other._notes)

    @property
    def description(self) -> str:
        return f"Add {len(self._notes)} Notes"


# ============================================================================
# 5. Transport Commands
# ============================================================================


class SetTempoCommand(ICommand):
    """设置速度命令"""

    def __init__(self, project: IProject, new_tempo: float):
        self._project = project
        self._new_tempo = new_tempo
        self._old_tempo = None
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            self._old_tempo = self._project.tempo
            self._project.tempo = self._new_tempo
            self._project.timeline.set_tempo(self._new_tempo)
            self._executed = True
            print(f"✓ Set tempo: {self._old_tempo} → {self._new_tempo} BPM")
            return True
        except Exception as e:
            print(f"✗ Failed to set tempo: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            self._project.tempo = self._old_tempo
            self._project.timeline.set_tempo(self._old_tempo)
            self._executed = False
            print(f"✓ Undone: Tempo restored to {self._old_tempo} BPM")
            return True
        except Exception as e:
            print(f"✗ Failed to undo tempo change: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        # 可以合并连续的速度更改
        return (isinstance(other, SetTempoCommand) and self._executed
                and not other._executed)

    def merge_with(self, other: ICommand):
        if not self.can_merge_with(other):
            raise ValueError("Cannot merge commands")
        # 保留最初的old_tempo，更新为最新的new_tempo
        self._new_tempo = other._new_tempo

    @property
    def description(self) -> str:
        return f"Set Tempo: {self._new_tempo} BPM"
