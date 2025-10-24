from ...interfaces import ICommand, IProject, INode
from typing import Any, List, Dict, Optional
from ...interfaces import ICommand, IProject, INode
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import PluginInstance
from ...models.clip_model import MIDIClip, Note


class AddInsertPluginCommand(ICommand):
    """添加插入效果命令"""

    def __init__(self,
                 project: IProject,
                 target_node_id: str,
                 plugin_instance: PluginInstance,
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
