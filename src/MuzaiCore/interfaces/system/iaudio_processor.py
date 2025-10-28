from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from ...models import TransportContext, NotePlaybackInfo


class IAudioProcessor(ABC):

    @abstractmethod
    def process_block(self, input_buffer: np.ndarray,
                      midi_events: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        """Processes one block of audio and MIDI data."""
        pass
