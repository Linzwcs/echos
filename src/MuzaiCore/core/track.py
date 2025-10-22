# file: src/MuzaiCore/core/track.py
import uuid
from typing import List, Optional, Dict

from .parameter import Parameter
from .plugin import PluginInstance
from .mixer import MixerChannel  # <-- Import the new MixerChannel
from ..interfaces import ITrack, IParameter, IMixerChannel
from ..subsystems.routing.routing_types import Port, PortType, PortDirection
from ..models.clip_model import AnyClip


class Track(ITrack):
    """
    Base class for all track types.
    This class is now primarily a container for timeline data (Clips).
    All signal processing is delegated to its `mixer_channel`.
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        self._node_id = node_id or str(uuid.uuid4())
        self.name = name
        self.clips: List[AnyClip] = []
        self._mixer_channel: IMixerChannel = MixerChannel()  # <-- Composition!
        self.is_armed = False  # For recording

        # Ports are still owned by the track, as it's the main routable entity
        self._input_ports: List[Port] = []
        self._output_ports: List[Port] = []

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def mixer_channel(self) -> IMixerChannel:
        return self._mixer_channel

    @property
    def is_armed(self) -> bool:
        return self._is_armed

    def get_parameters(self) -> Dict[str, IParameter]:
        """
        Gets all parameters for this track, which are primarily those
        of its associated mixer channel.
        """
        return self._mixer_channel.get_parameters()

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        all_ports = self._input_ports + self._output_ports
        if port_type:
            return [p for p in all_ports if p.port_type == port_type]
        return all_ports

    def process_block(self, input_buffer, midi_events, context):
        """
        The track's main processing function.
        1. Generates source signal from its clips (for InstrumentTrack).
        2. Passes the signal to its mixer channel for processing.
        """
        # Step 1: Generate source signal (specific to track type)
        # This part will be implemented by subclasses like InstrumentTrack.
        # For a basic AudioTrack, the source signal would be `input_buffer`.
        source_signal, source_midi = self._generate_source_signal(
            input_buffer, midi_events, context)

        # Step 2: Delegate all mixing and processing to the mixer channel
        return self.mixer_channel.process_block(source_signal, source_midi,
                                                context)

    def _generate_source_signal(self, input_buffer, midi_events, context):
        """
        Abstract method for subclasses to implement source signal generation.
        By default, it's a pass-through.
        """
        return input_buffer, midi_events


class InstrumentTrack(Track):
    """
    A track that holds MIDI clips and generates a signal.
    Its first plugin is typically a virtual instrument.
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # Instrument tracks generate MIDI, they don't receive it from outside.
        # But they can receive audio for side-chaining.
        self._input_ports = [
            Port(self.node_id, "sidechain_in", PortType.AUDIO,
                 PortDirection.INPUT, 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(self, input_buffer, midi_events, context):
        # In a real engine, this is where we would look at `self.clips`,
        # find all MIDI notes that start in the current block, and create
        # a list of MIDIEvent objects.
        # For mock, we'll just log it.

        # Let's pretend we found some notes from our clips
        notes_from_clips = []  # e.g., [MIDIEvent(...), ...]
        print(
            f"      -> Track '{self.name}': Generating MIDI from clips for beat {context.current_beat:.2f}"
        )

        # The instrument plugin in the mixer channel will process these notes.
        # The input_buffer is passed through for side-chaining purposes.
        return input_buffer, notes_from_clips


class AudioTrack(Track):
    """A track that holds audio clips or receives live audio input."""

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

    def _generate_source_signal(self, input_buffer, midi_events, context):
        # In a real engine, this method would read audio from its clips
        # and mix it with the live input_buffer.
        # For mock, we just pass the input through.
        return input_buffer, midi_events


# You can now easily define new track types that are pure mixers
class BusTrack(Track):
    """A track that acts as a bus/group, primarily for sub-mixing."""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # Buses only have audio inputs and outputs. They hold no clips.
        self.clips = []  # Ensure it has no clips
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]


class VCATrack(Track):
    """
    A special track that does not process audio but controls the faders
    of other MixerChannels. It is a node but its process_block does nothing.
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # VCA tracks have no ports and no clips
        self._input_ports = []
        self._output_ports = []
        self.clips = []

    def process_block(self, input_buffer, midi_events, context):
        # VCA faders do not process audio. Their influence is calculated
        # by the audio engine during the fader stage of the controlled tracks.
        return None
