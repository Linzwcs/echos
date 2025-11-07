import numpy as np
import pedalboard as pb
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple

from mido import Message
from ...models import TransportContext, AnyClip, MIDIClip, Note


class IAudioNode(ABC):

    def __init__(self, node_id: str, node_type: str, sample_rate: int,
                 block_size: int):
        self.node_id = node_id
        self.node_type = node_type
        self.sample_rate = sample_rate
        self.block_size = block_size

    @abstractmethod
    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:
        pass


NOTE_ON = 0
NOTE_OFF = 1


class BaseEffectNode(IAudioNode):

    def __init__(self,
                 node_id: str,
                 node_type: str,
                 sample_rate: int,
                 block_size: int,
                 output_channels: int = 2):
        super().__init__(node_id, node_type, sample_rate, block_size)
        self.pedalboard = pb.Pedalboard([])
        self.plugin_instance_map: Dict[str, pb.Plugin] = {}
        self.clips: List[AnyClip] = []
        self.volume: float = 1.0
        self.pan: float = 0.0
        self.muted: bool = False
        self._output_channels = output_channels
        self.latency_samples = 0

    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:

        mixed_input = np.zeros((2, self.block_size), dtype=np.float32)
        for input_audio in inputs.values():
            mixed_input += input_audio

        if self.muted:
            mixed_input.fill(0.0)
            return mixed_input

        processed_audio = self.pedalboard(mixed_input, self.sample_rate)

        processed_audio *= self.volume
        if self.pan != 0.0:
            angle = (self.pan + 1.0) * np.pi / 4.0
            left_gain = np.cos(angle)
            right_gain = np.sin(angle)
            processed_audio[0] *= left_gain
            processed_audio[1] *= right_gain

        return processed_audio

    def update_clips(self, clips: List[AnyClip]):
        self.clips = clips

    def add_clip(self, clip: AnyClip):
        self.clips.append(clip)

    def add_plugin(self, plugin_instance: pb.Plugin, instance_id: str,
                   index: int):

        if instance_id in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} already exists."
            )
            return

        if index >= len(self.pedalboard):
            self.pedalboard.append(plugin_instance)
        else:
            self.pedalboard.insert(index, plugin_instance)

        self.plugin_instance_map[instance_id] = plugin_instance
        print(
            f"[Node {self.node_id[:6]}] Added plugin {plugin_instance.name} at index {index}."
        )

    def remove_plugin(self, instance_id: str):
        if instance_id not in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} not found."
            )
            return
        instance_to_remove = self.plugin_instance_map.pop(instance_id)
        try:
            self.pedalboard.remove(instance_to_remove)
            print(
                f"[Node {self.node_id[:6]}] Removed plugin {instance_to_remove.name}."
            )
        except ValueError:

            print(
                f"[Node {self.node_id[:6]}] CRITICAL: Instance {instance_id[:6]} was in map but not in pedalboard list!"
            )

    def move_plugin(self, instance_id: str, new_index: int):
        if instance_id not in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} not found."
            )
            return
        plugin_instance = self.plugin_instance_map.get(instance_id)

        if plugin_instance:

            self.pedalboard.remove(plugin_instance)
            self.pedalboard.insert(new_index, plugin_instance)
            print(
                f"[Node {self.node_id[:6]}] Moved plugin {instance_id[:6]} to index {new_index}."
            )

    def set_plugin_parameter(self, instance_id: str, param_name: str,
                             value: any):
        plugin_instance = self.plugin_instance_map.get(instance_id)
        if plugin_instance:
            if hasattr(plugin_instance, param_name):
                setattr(plugin_instance, param_name, value)

    def set_mix_parameter(self, param_name: str, value: any):
        if param_name == "volume":
            self.volume = 10**(value / 20.0) if value > -96 else 0.0
        elif param_name == "pan":
            self.pan = np.clip(value, -1.0, 1.0)
        elif param_name == "muted":
            self.muted = bool(value)


class InstrumentTrackNode(BaseEffectNode):

    def __init__(self,
                 node_id: str,
                 node_type: str,
                 sample_rate: int,
                 block_size: int,
                 output_channels: int = 2):
        super().__init__(node_id, node_type, sample_rate, block_size,
                         output_channels)
        self.instrument = None

        self._active_notes: Dict[str, int] = {}
        self._sorted_events: List[Tuple[float, int, Note]] = []
        self._event_idx = 0
        self._needs_resort = True
        self._last_beat = -1.0  # 用于检测播放指针的跳跃

    def _prepare_events(self):

        self._sorted_events = []
        for clip in self.clips:
            if not isinstance(clip, MIDIClip):
                continue

            for note in clip.notes:
                note_start_beat = clip.start_beat + note.start_beat
                note_end_beat = note_start_beat + note.duration_beats

                self._sorted_events.append((note_start_beat, NOTE_ON, note))

                self._sorted_events.append((note_end_beat, NOTE_OFF, note))

        self._sorted_events.sort(key=lambda x: x[0])
        self._event_idx = 0
        self._needs_resort = False
        print(
            f"[Node {self.node_id[:6]}] Resorted {len(self._sorted_events)} MIDI events."
        )

    def update_clips(self, clips: List[AnyClip]):
        super().update_clips(clips)
        self._active_notes.clear()
        self._needs_resort = True

    def add_clip(self, clip: AnyClip):
        super().add_clip(clip)
        self._needs_resort = True

    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:
        assert self.instrument

        if self.muted or not self.instrument:
            return np.zeros((2, self.block_size), dtype=np.float32)

        if self._needs_resort:
            self._prepare_events()

        beats_per_block = (self.block_size /
                           self.sample_rate) * (context.tempo / 60.0)

        if abs(context.current_beat - self._last_beat) > beats_per_block * 2:

            self._event_idx = 0
            self._active_notes.clear()

        self._last_beat = context.current_beat

        block_duration_seconds = self.block_size / self.sample_rate
        beats_per_second = context.tempo / 60.0
        block_start_beat = context.current_beat
        block_end_beat = block_start_beat + beats_per_block

        midi_messages = []

        while self._event_idx < len(self._sorted_events):
            event_beat, event_type, note = self._sorted_events[self._event_idx]

            if event_beat >= block_end_beat:
                break

            if event_beat >= block_start_beat:
                time_in_beats = event_beat - block_start_beat
                time_in_seconds = max(0, time_in_beats / beats_per_second)

                if event_type == NOTE_ON:
                    if note.note_id not in self._active_notes:
                        msg = Message('note_on',
                                      note=note.pitch,
                                      velocity=note.velocity,
                                      time=time_in_seconds)
                        midi_messages.append(msg)
                        self._active_notes[note.note_id] = note.pitch

                elif event_type == NOTE_OFF:
                    if note.note_id in self._active_notes:
                        msg = Message('note_off',
                                      note=note.pitch,
                                      velocity=0,
                                      time=time_in_seconds)
                        midi_messages.append(msg)
                        del self._active_notes[note.note_id]

            self._event_idx += 1

        try:
            audio_after_instrument = self.instrument.process(
                midi_messages=midi_messages,
                duration=block_duration_seconds,
                sample_rate=self.sample_rate,
                buffer_size=self.block_size,
                num_channels=2,
                reset=False)
        except Exception as e:
            print(
                f"[Node {self.node_id[:6]}] Error processing instrument: {e}")
            return np.zeros((2, self.block_size), dtype=np.float32)

        if len(self.pedalboard) > 0:
            try:
                audio_after_instrument = self.pedalboard(
                    audio_after_instrument, self.sample_rate)
            except Exception as e:
                print(
                    f"[Node {self.node_id[:6]}] Error processing effects: {e}")

        final_audio = audio_after_instrument * self.volume

        if self.pan != 0.0:
            angle = (self.pan + 1.0) * np.pi / 4.0
            final_audio[0] *= np.cos(angle)
            final_audio[1] *= np.sin(angle)

        return final_audio

    def add_plugin(self, plugin_instance: pb.Plugin, instance_id: str,
                   index: int):

        if instance_id in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} already exists."
            )
            return

        if plugin_instance.is_instrument:
            if self.instrument is not None:
                print(
                    f"[Node {self.node_id[:6]}] Warning: Replacing existing instrument"
                )

            self.instrument = plugin_instance
            print(
                f"[Node {self.node_id[:6]}] Set instrument: {plugin_instance.name}"
            )
        else:
            actual_index = index - (1 if self.instrument else 0)

            if actual_index < 0:
                actual_index = 0

            if actual_index >= len(self.pedalboard):
                self.pedalboard.append(plugin_instance)
            else:
                self.pedalboard.insert(actual_index, plugin_instance)

            print(
                f"[Node {self.node_id[:6]}] Added effect {plugin_instance.name} at index {index}"
            )

    def remove_plugin(self, instance_id: str):

        if instance_id not in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} not found."
            )
            return

        instance_to_remove = self.plugin_instance_map.pop(instance_id)

        if instance_to_remove.is_instrument:
            self.instrument = None
            print(
                f"[Node {self.node_id[:6]}] Removed instrument: {instance_to_remove.name}"
            )
        else:
            try:
                self.pedalboard.remove(instance_to_remove)
                print(
                    f"[Node {self.node_id[:6]}] Removed effect: {instance_to_remove.name}"
                )
            except ValueError:
                print(
                    f"[Node {self.node_id[:6]}] CRITICAL: Instance {instance_id[:6]} "
                    f"was in map but not in pedalboard list!")


class BusNode(BaseEffectNode):

    pass


class AudioTrackNode(BaseEffectNode):

    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:
        return super().process(context, inputs)
