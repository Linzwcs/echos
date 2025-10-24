from typing import Any, List, Dict, Optional
from ...interfaces import ICommand, IProject
from ...models.clip_model import MIDIClip, Note


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
