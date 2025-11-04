# file: src/MuzaiCore/backends/pedalboard/nodes.py
import numpy as np
import pedalboard as pb
from abc import ABC, abstractmethod
from typing import List, Dict

from mido import Message
from ...models import TransportContext, AnyClip, MIDIClip, AudioClip


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


class BaseEffectNode(IAudioNode):

    def __init__(self, node_id: str, node_type: str, sample_rate: int,
                 block_size: int):
        super().__init__(node_id, node_type, sample_rate, block_size)
        self.pedalboard = pb.Pedalboard([])
        self.plugin_instance_map: Dict[str, pb.Plugin] = {}
        self.clips: List[AnyClip] = []
        self.volume: float = 1.0
        self.pan: float = 0.0
        self.muted: bool = False
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

    def set_mix_parameter(self, param_name: str, value: any):
        if param_name == "volume":
            self.volume = 10**(value / 20.0) if value > -96 else 0.0
        elif param_name == "pan":
            self.pan = np.clip(value, -1.0, 1.0)
        elif param_name == "muted":
            self.muted = bool(value)

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

    def set_plugin_parameter(self, instance_id: str, param_name: str,
                             value: any):
        plugin_instance = self.plugin_instance_map.get(instance_id)
        if plugin_instance:
            if hasattr(plugin_instance, param_name):
                setattr(plugin_instance, param_name, value)


class InstrumentTrackNode(BaseEffectNode):

    def __init__(self, node_id: str, node_type: str, sample_rate: int,
                 block_size: int):
        super().__init__(node_id, node_type, sample_rate, block_size)
        self.instrutment = None
        self._active_notes: Dict[str, tuple[int, float]] = {}

    def update_clips(self, clips: List[AnyClip]):
        super().update_clips(clips)
        self._active_notes.clear()

    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:
        assert self.instrutment
        # 如果静音或没有乐器插件，直接返回静音
        if self.muted or not self.instrutment:
            return np.zeros((2, self.block_size), dtype=np.float32)

        # 计算当前处理块的时间信息
        block_duration_seconds = self.block_size / self.sample_rate
        beats_per_second = context.tempo / 60.0
        block_start_beat = context.current_beat
        block_end_beat = block_start_beat + (beats_per_second *
                                             block_duration_seconds)

        midi_messages = []

        # --- 阶段 1: 检查并触发新的 Note On 事件 ---
        for clip in self.clips:
            if not isinstance(clip, MIDIClip):
                continue

            # 简单的剪辑范围检查，优化性能
            clip_start_beat = clip.start_beat
            clip_end_beat = clip_start_beat + clip.duration_beats
            if max(block_start_beat,
                   clip_start_beat) >= min(block_end_beat, clip_end_beat):
                continue

            for note in clip.notes:
                note_start_beat = clip_start_beat + note.start_beat

                # 如果音符在当前块内开始，并且它不在已激活列表中
                if block_start_beat <= note_start_beat < block_end_beat:
                    if note.note_id not in self._active_notes:
                        # 计算相对于块开始的时间戳
                        time_in_beats = note_start_beat - block_start_beat
                        time_in_seconds = time_in_beats / beats_per_second

                        msg = Message('note_on',
                                      note=note.pitch,
                                      velocity=note.velocity,
                                      time=time_in_seconds)
                        midi_messages.append(msg)

                        # 将音符添加到激活列表，记录其结束时间
                        note_end_beat = note_start_beat + note.duration_beats
                        self._active_notes[note.note_id] = (note.pitch,
                                                            note_end_beat)

        # --- 阶段 2: 检查并触发已激活音符的 Note Off 事件 ---
        # 使用 list(self._active_notes.items()) 来创建一个副本，因为我们可能会在循环中修改字典
        notes_to_remove = []
        for note_id, (pitch, note_end_beat) in self._active_notes.items():
            # 如果音符的结束时间落在当前块内
            if block_start_beat <= note_end_beat < block_end_beat:
                # 计算相对于块开始的时间戳
                time_in_beats = note_end_beat - block_start_beat
                time_in_seconds = time_in_beats / beats_per_second

                msg = Message('note_off',
                              note=pitch,
                              velocity=0,
                              time=time_in_seconds)
                midi_messages.append(msg)

                # 标记此音符以便从激活列表中移除
                notes_to_remove.append(note_id)

        # 从激活列表中移除已经结束的音符
        for note_id in notes_to_remove:
            if note_id in self._active_notes:
                del self._active_notes[note_id]

        audio_after_instrument = self.instrutment.process(
            midi_messages=midi_messages,
            duration=block_duration_seconds,
            sample_rate=self.sample_rate,
            buffer_size=self.block_size,
            num_channels=2,
            reset=False)

        # 处理音量和声像
        final_audio = audio_after_instrument
        final_audio *= self.volume
        if self.pan != 0.0:
            angle = (self.pan + 1.0) * np.pi / 4.0
            final_audio[0] *= np.cos(angle)
            final_audio[1] *= np.sin(angle)

        if midi_messages:
            max_amplitude = np.max(np.abs(final_audio))
            print(f"    插件输出最大振幅: {max_amplitude:.6f}")
            if max_amplitude < 1e-5:
                print("    !!! 警告: 插件输出了静音 !!!")

        return final_audio

    def add_plugin(self, plugin_instance: pb.Plugin, instance_id: str,
                   index: int):

        if instance_id in self.plugin_instance_map:
            print(
                f"[Node {self.node_id[:6]}] Warning: Plugin instance {instance_id[:6]} already exists."
            )
            return

        if plugin_instance.is_instrument:
            self.instrutment = plugin_instance
        else:
            index = index - int(bool(self.instrutment))
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
        if instance_to_remove.is_instrument:
            self.instrutment = None
        else:
            self.pedalboard.remove(instance_to_remove)
        print(
            f"[Node {self.node_id[:6]}] Removed plugin {instance_to_remove.name}."
        )


class BusNode(BaseEffectNode):

    pass


class AudioTrackNode(BaseEffectNode):

    def process(self, context: TransportContext,
                inputs: Dict[str, np.ndarray]) -> np.ndarray:
        return super().process(context, inputs)
