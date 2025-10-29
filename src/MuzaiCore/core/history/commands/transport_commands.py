from typing import Any, List, Dict, Optional
from ...track import InstrumentTrack, AudioTrack, BusTrack
from ...plugin import Plugin
from ....models.clip_model import MIDIClip, Note
from ....interfaces import ICommand, IProject, INode


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


class SetTimeSignatureCommand:
    """设置拍号命令（临时实现）"""

    def __init__(self, project, numerator: int, denominator: int):
        self._project = project
        self._new_time_signature = (numerator, denominator)
        self._old_time_signature = None
        self._executed = False

    def execute(self) -> bool:
        if self._executed:
            return False
        try:
            self._old_time_signature = self._project.time_signature
            self._project.time_signature = self._new_time_signature
            self._executed = True
            print(f"✓ Set time signature: {self._old_time_signature} → "
                  f"{self._new_time_signature}")
            return True
        except Exception as e:
            print(f"✗ Failed to set time signature: {e}")
            return False

    def undo(self) -> bool:
        if not self._executed:
            return False
        try:
            self._project.time_signature = self._old_time_signature
            self._executed = False
            print(
                f"✓ Undone: Time signature restored to {self._old_time_signature}"
            )
            return True
        except Exception as e:
            print(f"✗ Failed to undo time signature change: {e}")
            return False

    def can_merge_with(self, other) -> bool:
        return (isinstance(other, SetTimeSignatureCommand) and self._executed
                and not other._executed)

    def merge_with(self, other):
        if not self.can_merge_with(other):
            raise ValueError("Cannot merge commands")
        self._new_time_signature = other._new_time_signature

    @property
    def description(self) -> str:
        return f"Set Time Signature: {self._new_time_signature[0]}/{self._new_time_signature[1]}"
