from typing import Any, List, Optional
from ....interfaces import IParameter, ITrack
from ....models import MIDIClip, Note
from ..command_base import BaseCommand


class SetParameterCommand(BaseCommand):

    def __init__(self, parameter: IParameter, new_value: Any):
        super().__init__(f"Set {parameter.name} to {new_value}")
        self._parameter = parameter
        self._new_value = new_value
        self._old_value = parameter.value

    def _do_execute(self) -> bool:
        self._parameter.set_value(self._new_value, immediate=True)
        return True

    def _do_undo(self) -> bool:
        self._parameter.set_value(self._old_value, immediate=True)
        return True

    def can_merge_with(self, other: BaseCommand) -> bool:
        return (isinstance(other, SetParameterCommand)
                and other._parameter is self._parameter)

    def merge_with(self, other: 'SetParameterCommand'):
        self._new_value = other._new_value
        self.description = f"Set {self._parameter.name} to {self._new_value}"


class CreateMidiClipCommand(BaseCommand):

    def __init__(self,
                 track: ITrack,
                 start_beat: float,
                 duration_beats: float,
                 name: str,
                 clip_id: str = None):

        super().__init__(f"Create MIDI Clip '{name}'")
        self._track = track
        self._clip_data = {
            "start_beat": start_beat,
            "duration_beats": duration_beats,
            "name": name,
        }
        if clip_id:
            self._clip_data["clip_id"] = clip_id
        self._created_clip: Optional[MIDIClip] = None

    def _do_execute(self) -> bool:

        self._created_clip = MIDIClip(**self._clip_data)
        self._track.add_clip(self._created_clip)
        return True

    def _do_undo(self) -> bool:
        if self._created_clip:
            return self._track.remove_clip(self._created_clip.clip_id)
        return False


class AddNotesToClipCommand(BaseCommand):

    def __init__(self, clip: MIDIClip, notes_to_add: List[Note]):
        note_count = len(notes_to_add)
        super().__init__(
            f"Add {note_count} note{'s' if note_count > 1 else ''} to clip '{clip.name}'"
        )
        self._clip = clip
        self._notes_to_add = notes_to_add

    def _do_execute(self) -> bool:
        initial_count = len(self._clip.notes)
        for note in self._notes_to_add:
            self._clip.notes.add(note)
        return len(self._clip.notes) > initial_count

    def _do_undo(self) -> bool:
        initial_count = len(self._clip.notes)
        for note in self._notes_to_add:
            if note in self._clip.notes:
                self._clip.notes.remove(note)
        return len(self._clip.notes) < initial_count
