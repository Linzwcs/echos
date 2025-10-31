# file: src/MuzaiCore/core/history/commands/transport_commands.py
from typing import Tuple
from ..command_base import BaseCommand
from ....interfaces.system import ITimeline


class SetTempoCommand(BaseCommand):
    """一个设置速度的可撤销命令。"""

    def __init__(self, timeline: ITimeline, new_bpm: float):
        super().__init__(f"Set Tempo to {new_bpm:.2f} BPM")
        self._timeline = timeline
        self._new_bpm = new_bpm
        # 在执行前记录旧值，以便撤销
        self._old_bpm = timeline.tempo

    def _do_execute(self) -> bool:
        self._timeline.set_tempo(self._new_bpm)
        return True

    def _do_undo(self) -> bool:
        self._timeline.set_tempo(self._old_bpm)
        return True

    def can_merge_with(self, other: BaseCommand) -> bool:
        """如果连续拖动速度滑块，可以合并命令。"""
        return isinstance(
            other, SetTempoCommand) and self._timeline is other._timeline

    def merge_with(self, other: 'SetTempoCommand'):
        """合并时，只需更新最终的目标速度值。"""
        self._new_bpm = other._new_bpm
        self.description = f"Set Tempo to {self._new_bpm:.2f} BPM"


class SetTimeSignatureCommand(BaseCommand):
    """一个设置拍号的可撤销命令。"""

    def __init__(self, timeline: ITimeline, numerator: int, denominator: int):
        super().__init__(f"Set Time Signature to {numerator}/{denominator}")
        self._timeline = timeline
        self._new_ts = (numerator, denominator)
        self._old_ts = timeline.time_signature

    def _do_execute(self) -> bool:
        self._timeline.set_time_signature(self._new_ts[0], self._new_ts[1])
        return True

    def _do_undo(self) -> bool:
        self._timeline.set_time_signature(self._old_ts[0], self._old_ts[1])
        return True
