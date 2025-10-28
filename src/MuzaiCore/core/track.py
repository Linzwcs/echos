# file: src/MuzaiCore/core/track.py

import uuid
from typing import List, Optional, Dict, Set, Tuple
import numpy as np

from ..interfaces.system import ITrack, IMixerChannel
from ..models import (Port, PortType, PortDirection, AnyClip, MIDIClip,
                      AudioClip, Note, TransportContext, NotePlaybackInfo)
from .mixer import MixerChannel

# Note: TrackRecordMode is now in models/node_model.py
from ..models import TrackRecordMode


class Track(ITrack):
    """
    Base class for all track types. A track is a container for timeline
    data (clips) and delegates all signal processing to its associated
    mixer channel.
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        self._node_id = node_id or f"track_{uuid.uuid4()}"
        self._name = name
        self.clips: Set[AnyClip] = set()

        # Composition: Every track owns a mixer channel.
        self._mixer_channel: IMixerChannel = MixerChannel(self._node_id)

        # State properties
        self._is_armed: bool = False
        self._record_mode: TrackRecordMode = TrackRecordMode.NORMAL
        self._input_source_id: Optional[str] = None
        self._is_frozen: bool = False
        self._frozen_audio_path: Optional[str] = None

        # UI properties
        self.color: Optional[str] = None
        self.icon: Optional[str] = None

        # Ports are owned by the track as it's the main routable entity
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
        if not frozen:
            self._frozen_audio_path = None  # Clear path when unfreezing

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        all_ports = self._input_ports + self._output_ports
        if port_type:
            return [p for p in all_ports if p.port_type == port_type]
        return all_ports

    def add_clip(self, clip: AnyClip):
        self.clips.add(clip)

    def remove_clip(self, clip_id: str) -> bool:
        clip_to_remove = next((c for c in self.clips if c.clip_id == clip_id),
                              None)
        if clip_to_remove:
            self.clips.remove(clip_to_remove)
            return True
        return False

    def process_block(self, input_buffer: np.ndarray,
                      notes: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        """
        The main processing function for a track.
        1. Generates source signal (from clips or live input).
        2. Passes the signal to the mixer channel for processing.
        """
        if self._is_frozen and self._frozen_audio_path:
            # In a real implementation, this would read pre-rendered audio from disk.
            return np.zeros((2, context.block_size), dtype=np.float32)

        # Step 1: Generate source signal (implemented by subclasses).
        # This combines external input with internally generated signals (from clips).
        source_audio, source_notes = self._generate_source_signal(
            input_buffer, notes, context)

        # Step 2: Delegate all mixing and effects processing to the mixer channel.
        return self.mixer_channel.process_block(source_audio, source_notes,
                                                context)

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        """
        Abstract method for subclasses to generate their source signal.
        Default implementation is pass-through.
        """
        return input_buffer, notes


class InstrumentTrack(Track):
    """A track that holds MIDI clips and generates musical note data."""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # An instrument track can receive audio for sidechaining purposes.
        self._input_ports = [
            Port(self.node_id, "sidechain_in", PortType.AUDIO,
                 PortDirection.INPUT, 2)
        ]
        # It always outputs audio.
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        """
        Generates NotePlaybackInfo events from its MIDIClips for the current block.
        These new notes are added to any notes coming from upstream (e.g., live MIDI input).
        """
        generated_notes = self._collect_notes_in_range(context)

        # The instrument itself doesn't generate audio, it generates note data
        # for a synth plugin to process. So, the input audio is just passed through.
        return input_buffer, notes + generated_notes

    def _collect_notes_in_range(
            self, context: TransportContext) -> List[NotePlaybackInfo]:
        """Scans clips and converts MIDI Note data to real-time NotePlaybackInfo."""
        notes_to_play = []

        # Calculate the beat range for the current processing block
        beats_per_second = context.tempo / 60.0
        seconds_per_block = context.block_size / context.sample_rate
        beats_per_block = seconds_per_block * beats_per_second
        start_beat_of_block = context.current_beat
        end_beat_of_block = start_beat_of_block + beats_per_block

        for clip in self.clips:
            if not isinstance(clip, MIDIClip):
                continue

            # Check if the clip is active in the current time range
            if clip.start_beat > end_beat_of_block or \
               (clip.start_beat + clip.duration_beats) < start_beat_of_block:
                continue

            for note in clip.notes:
                note_start_beat = clip.start_beat + note.start_beat

                # Check if this specific note starts within the current block
                if start_beat_of_block <= note_start_beat < end_beat_of_block:
                    # Convert note's start time from beats to a sample offset within the block
                    beat_offset_in_block = note_start_beat - start_beat_of_block
                    time_offset_in_block = (beat_offset_in_block /
                                            beats_per_second)
                    sample_offset = int(time_offset_in_block *
                                        context.sample_rate)

                    # Convert note's duration from beats to total samples
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

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
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
        """
        Reads audio from its clips and mixes it with the live input buffer.
        """
        # In a real implementation, this would read from audio files on disk.
        clip_audio = self._read_clips_in_range(context)

        # Mix the audio from clips with the audio from upstream routing
        mixed_audio = clip_audio + input_buffer

        # Audio tracks typically don't generate notes, so they are passed through.
        return mixed_audio, notes

    def _read_clips_in_range(self, context: TransportContext) -> np.ndarray:
        """Reads audio from AudioClip data for the current block."""
        # This is a placeholder for a complex audio file reading/resampling engine.
        return np.zeros((2, context.block_size), dtype=np.float32)


class BusTrack(Track):
    """A track that acts as a bus/group for sub-mixing."""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # Buses only have audio inputs and outputs; they don't hold clips.
        self.clips.clear()
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 8)  # More channels
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(
        self, input_buffer: np.ndarray, notes: List[NotePlaybackInfo],
        context: TransportContext
    ) -> Tuple[np.ndarray, List[NotePlaybackInfo]]:
        """A bus only processes audio routed into it; it doesn't generate its own signal."""
        # It also clears any incoming notes, as it's an audio-only path.
        return input_buffer, []


class MasterTrack(BusTrack):
    """The final output track in the signal chain."""

    def __init__(self, name: str = "Master", node_id: Optional[str] = None):
        super().__init__(name, node_id
                         or "master_track")  # Often has a fixed ID
        # The master track's output is conceptually connected to the hardware.
        self._output_ports = [
            Port(self.node_id, "hardware_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]
