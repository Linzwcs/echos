# file: src/MuzaiCore/interfaces/IAudioProcessor.py
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from ..models.engine_model import TransportContext, MIDIEvent


class IAudioProcessor(ABC):

    @abstractmethod
    def process_block(self, input_buffer: np.ndarray,
                      midi_events: List[MIDIEvent],
                      context: TransportContext) -> np.ndarray:
        """Processes one block of audio and MIDI data."""
        pass
