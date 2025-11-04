# file: src/MuzaiCore/core/history/commands/transport_commands.py
from typing import Tuple
from ..command_base import BaseCommand
from ....interfaces.system import IDomainTimeline


class SetTempoCommand(BaseCommand):
    """一个设置速度的可撤销命令。"""

    def __init__(self, timeline: IDomainTimeline, beat: float, new_bpm: float):
        super().__init__(f"Set Tempo to {new_bpm:.2f} BPM")
        self._timeline = timeline
        self._beat = beat
        self._new_bpm = new_bpm
        self._old_state = timeline.timeline_state

    def _do_execute(self) -> bool:
        self._timeline.add_tempo(beat=self._beat, bpm=self._new_bpm)
        return True

    def _do_undo(self) -> bool:
        self._timeline.set_state(self._old_state)
        return True

    def can_merge_with(self, other: BaseCommand) -> bool:

        return isinstance(
            other, SetTempoCommand) and self._timeline is other._timeline

    def merge_with(self, other: 'SetTempoCommand'):
        self._new_bpm = other._new_bpm
        self.description = f"Set Tempo to {self._new_bpm:.2f} BPM"


class SetTimeSignatureCommand(BaseCommand):

    def __init__(self, timeline: IDomainTimeline, beat: float, numerator: int,
                 denominator: int):
        super().__init__(
            f"Set Time Signature to {numerator}/{denominator} at beat {beat}")
        self._timeline = timeline
        self._beat = beat
        self._new_ts = (numerator, denominator)
        self._old_state = timeline.timeline_state

    def _do_execute(self) -> bool:
        self._timeline.add_time_signature(beat=self._beat,
                                          numerator=self._new_ts[0],
                                          denominator=self._new_ts[1])
        return True

    def _do_undo(self) -> bool:
        self._timeline.set_state(self._old_state)
        return True
