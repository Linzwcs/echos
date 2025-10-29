# file: src/MuzaiCore/core/track.py
from enum import Flag, auto, Enum
import uuid
from typing import List, Optional, Dict, Set, Tuple
import numpy as np

from ..interfaces.system import ITrack, IMixerChannel, IEventBus
from ..models import (Port, PortType, PortDirection, AnyClip, MIDIClip,
                      AudioClip, Note, TransportContext, NotePlaybackInfo)
from ..models.event_model import ClipAdded, ClipRemoved
from .mixer import MixerChannel
from .parameter import VCAParameter


# (VCAControlMode and TrackRecordMode enums remain unchanged)
class VCAControlMode(Flag):
    NONE = 0
    VOLUME = auto()
    PAN = auto()
    MUTE = auto()
    ALL = VOLUME | PAN | MUTE

    def controls_volume(self) -> bool:
        return bool(self & VCAControlMode.VOLUME)

    def controls_pan(self) -> bool:
        return bool(self & VCAControlMode.PAN)

    def controls_mute(self) -> bool:
        return bool(self & VCAControlMode.MUTE)


class TrackRecordMode(Enum):
    NORMAL = "normal"
    OVERDUB = "overdub"
    REPLACE = "replace"
    LOOP = "loop"


class Track(ITrack):
    """
    Base class for all track types.
    """

    def __init__(
            self,
            name: str,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        self._node_id = node_id or f"track_{uuid.uuid4()}"
        self._name = name
        self._event_bus = event_bus  # <-- 新增
        self.clips: Set[AnyClip] = set()

        # Composition: Every track owns a mixer channel.
        self._mixer_channel: IMixerChannel = MixerChannel(
            self._event_bus, self._node_id)

        self._is_armed: bool = False
        self._record_mode: TrackRecordMode = TrackRecordMode.NORMAL
        self._input_source_id: Optional[str] = None
        self._is_frozen: bool = False
        self._frozen_audio_path: Optional[str] = None
        self.color: Optional[str] = None
        self.icon: Optional[str] = None
        self._input_ports: List[Port] = []
        self._output_ports: List[Port] = []

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def mixer_channel(self) -> IMixerChannel:
        return self._mixer_channel

    @property
    def is_armed(self) -> bool:
        return self._is_armed

    @property
    def record_mode(self) -> TrackRecordMode:
        return self._record_mode

    @property
    def input_source_id(self) -> Optional[str]:
        return self._input_source_id

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    def set_armed(self, armed: bool):
        self._is_armed = armed

    def set_record_mode(self, mode: TrackRecordMode):
        self._record_mode = mode

    def set_input_source(self, source_id: Optional[str]):
        self._input_source_id = source_id

    def set_frozen(self, frozen: bool, flatten: bool = False):
        self._is_frozen = frozen
        if not frozen: self._frozen_audio_path = None

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        all_ports = self._input_ports + self._output_ports
        if port_type:
            return [p for p in all_ports if p.port_type == port_type]
        return all_ports

    # subscribe_clip_events 方法被移除

    def add_clip(self, clip: AnyClip):
        self.clips.add(clip)
        # 发布事件
        self._event_bus.publish(
            ClipAdded(owner_track_id=self.node_id, clip=clip))

    def remove_clip(self, clip_id: str) -> bool:
        clip_to_remove = next((c for c in self.clips if c.clip_id == clip_id),
                              None)
        if clip_to_remove:
            self.clips.remove(clip_to_remove)
            # 发布事件
            self._event_bus.publish(
                ClipRemoved(owner_track_id=self.node_id, clip_id=clip_id))
            return True
        return False

    def process_block(self, input_buffer: np.ndarray,
                      notes: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        if self._is_frozen and self._frozen_audio_path:
            return np.zeros((2, context.block_size), dtype=np.float32)

        source_audio, source_notes = self._generate_source_signal(
            input_buffer, notes, context)
        return self.mixer_channel.process_block(source_audio, source_notes,
                                                context)

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        return input_buffer, notes

    def get_parameters(self):
        return self._mixer_channel.get_parameters()


class InstrumentTrack(Track):
    """A track that holds MIDI clips and generates musical note data."""

    def __init__(
            self,
            name: str,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        super().__init__(name, event_bus, node_id)  # <-- 传递
        self._input_ports = [
            Port(self.node_id, "sidechain_in", PortType.AUDIO,
                 PortDirection.INPUT, 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        generated_notes = self._collect_notes_in_range(context)
        return input_buffer, notes + generated_notes

    def _collect_notes_in_range(
            self, context: TransportContext) -> List[NotePlaybackInfo]:
        notes_to_play = []
        beats_per_second = context.tempo / 60.0
        seconds_per_block = context.block_size / context.sample_rate
        beats_per_block = seconds_per_block * beats_per_second
        start_beat_of_block = context.current_beat
        end_beat_of_block = start_beat_of_block + beats_per_block

        for clip in self.clips:
            if not isinstance(clip, MIDIClip): continue
            if clip.start_beat > end_beat_of_block or \
               (clip.start_beat + clip.duration_beats) < start_beat_of_block:
                continue

            for note in clip.notes:
                note_start_beat = clip.start_beat + note.start_beat
                if start_beat_of_block <= note_start_beat < end_beat_of_block:
                    beat_offset_in_block = note_start_beat - start_beat_of_block
                    time_offset_in_block = (beat_offset_in_block /
                                            beats_per_second)
                    sample_offset = int(time_offset_in_block *
                                        context.sample_rate)
                    duration_seconds = (note.duration_beats / beats_per_second)
                    duration_samples = int(duration_seconds *
                                           context.sample_rate)
                    notes_to_play.append(
                        NotePlaybackInfo(note_pitch=note.pitch,
                                         velocity=note.velocity,
                                         start_sample=sample_offset,
                                         duration_samples=duration_samples))
        return notes_to_play


class AudioTrack(Track):
    """A track that holds audio clips or processes live audio input."""

    def __init__(
            self,
            name: str,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        super().__init__(name, event_bus, node_id)  # <-- 传递
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        clip_audio = self._read_clips_in_range(context)
        mixed_audio = clip_audio + input_buffer
        return mixed_audio, notes

    def _read_clips_in_range(self, context: TransportContext) -> np.ndarray:
        return np.zeros((2, context.block_size), dtype=np.float32)


class BusTrack(Track):
    """A track that acts as a bus/group for sub-mixing."""

    def __init__(
            self,
            name: str,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        super().__init__(name, event_bus, node_id)  # <-- 传递
        self.clips.clear()
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 8)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        return input_buffer, []


class MasterTrack(BusTrack):
    """The final output track in the signal chain."""

    def __init__(
            self,
            name: str = "Master",
            event_bus: Optional[IEventBus] = None,  # <-- 新增
            node_id: Optional[str] = None):
        super().__init__(name, event_bus, node_id or "master_track")  # <-- 传递
        self._output_ports = [
            Port(self.node_id, "hardware_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]


class VCATrack(ITrack):
    """
    VCA轨道 - 纯控制层实现
    """

    def __init__(
            self,
            name: str,
            event_bus: IEventBus,  # <-- 新增
            node_id: Optional[str] = None):
        self._node_id = node_id or f"vca_{uuid.uuid4()}"
        self._name = name
        self._event_bus = event_bus  # <-- 新增

        self._volume_control = VCAParameter(self.node_id, "vca_volume", 0.0,
                                            event_bus, -100.0, 12.0)
        self._pan_control = VCAParameter(self.node_id, "vca_pan", 0.0,
                                         event_bus, -1.0, 1.0)
        self._mute_control = VCAParameter(self.node_id, "vca_mute", False,
                                          event_bus)

        self._controlled_tracks: Dict[str, 'VCAControlMode'] = {}
        self._parent_vca_id: Optional[str] = None
        self.color: Optional[str] = None
        self.icon: Optional[str] = None
        self._input_ports: List[Port] = []
        self._output_ports: List[Port] = []

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        return []

    def process_block(self, input_buffer: np.ndarray,
                      notes: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        return np.zeros((2, context.block_size), dtype=np.float32)

    @property
    def mixer_channel(self) -> IMixerChannel:
        raise AttributeError("VCA Track does not have a mixer channel")

    @property
    def is_armed(self) -> bool:
        return False

    @property
    def record_mode(self):
        return None

    @property
    def input_source_id(self) -> Optional[str]:
        return None

    @property
    def is_frozen(self) -> bool:
        return False

    def set_armed(self, armed: bool):
        pass

    def set_frozen(self, frozen: bool, flatten: bool = False):
        pass

    @property
    def volume_control(self) -> 'VCAParameter':
        return self._volume_control

    @property
    def pan_control(self) -> 'VCAParameter':
        return self._pan_control

    @property
    def mute_control(self) -> 'VCAParameter':
        return self._mute_control

    def add_controlled_track(self,
                             track_id: str,
                             mode: 'VCAControlMode' = None):
        if mode is None: mode = VCAControlMode.ALL
        self._controlled_tracks[track_id] = mode
        # 注意: VCA 分配目前没有定义相应的事件

    def remove_controlled_track(self, track_id: str):
        if track_id in self._controlled_tracks:
            del self._controlled_tracks[track_id]
            # 注意: VCA 分配目前没有定义相应的事件

    def get_controlled_tracks(self) -> Dict[str, 'VCAControlMode']:
        return dict(self._controlled_tracks)

    def set_parent_vca(self, parent_vca_id: Optional[str]):
        self._parent_vca_id = parent_vca_id

    @property
    def parent_vca_id(self) -> Optional[str]:
        return self._parent_vca_id

    def apply_control_to_track(self, track: ITrack, context: TransportContext):
        if track.node_id not in self._controlled_tracks: return
        mode = self._controlled_tracks[track.node_id]
        try:
            mixer = track.mixer_channel
        except AttributeError:
            if isinstance(track, VCATrack): self._apply_to_vca(track, context)
            return

        if mode.controls_volume():
            vca_volume = self._volume_control.get_value_at(context)
            track_volume = mixer.volume
            combined_volume = track_volume.value + vca_volume
            track_volume._set_value_internal(combined_volume)

        if mode.controls_pan():
            vca_pan = self._pan_control.get_value_at(context)
            track_pan = mixer.pan
            combined_pan = track_pan.value + vca_pan
            combined_pan = max(-1.0, min(1.0, combined_pan))
            track_pan._set_value_internal(combined_pan)

        if mode.controls_mute():
            if self._mute_control.get_value_at(context):
                mixer.is_muted = True

    def _apply_to_vca(self, child_vca: 'VCATrack', context: TransportContext):
        mode = self._controlled_tracks[child_vca.node_id]
        if mode.controls_volume():
            parent_volume = self._volume_control.get_value_at(context)
            child_volume = child_vca._volume_control.value
            child_vca._volume_control._set_value_internal(child_volume +
                                                          parent_volume)
        if mode.controls_pan():
            parent_pan = self._pan_control.get_value_at(context)
            child_pan = child_vca._pan_control.value
            child_vca._pan_control._set_value_internal(
                max(-1.0, min(1.0, child_pan + parent_pan)))
        if mode.controls_mute() and self._mute_control.get_value_at(context):
            child_vca._mute_control._set_value_internal(True)

    def get_parameters(self) -> Dict[str, VCAParameter]:
        return {
            "vca_volume": self._volume_control,
            "vca_pan": self._pan_control,
            "vca_mute": self._mute_control
        }
