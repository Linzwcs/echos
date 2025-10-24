# file: src/MuzaiCore/subsystems/commands/node_commands.py
from ...interfaces import ICommand, IProject, INode
from typing import Any, List, Dict, Optional
from ...interfaces import ICommand, IProject, INode
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import PluginInstance
from ...models.clip_model import MIDIClip, Note


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


# class CreateTrackCommand(ICommand):
#
#     def __init__(self, project: IProject, track: INode):
#         self._project = project
#         self._track = track
#         self._track_id = track.node_id
#
#     def execute(self) -> bool:
#         try:
#             self._project.add_node(self._track)
#             print(f"Executed: Created track {self._track_id}")
#             return True
#         except ValueError:
#             return False
#
#     def undo(self) -> bool:
#         try:
#             self._project.remove_node(self._track_id)
#             print(f"Undone: Removed track {self._track_id}")
#             return True
#         except ValueError:
#             return False
