# file: src/MuzaiCore/backends/real/plugin_adapter.py
import numpy as np
from typing import List

from ...core.plugin import Plugin  # Inherits state management
from ...models import TransportContext, NotePlaybackInfo


class RealPlugin(Plugin):
    """
    A concrete IPlugin implementation for the 'real' backend.
    It extends the standard PluginInstance state container with actual
    Python-based DSP processing logic.
    """

    def process_block(self, input_buffer: np.ndarray,
                      notes: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        """
        Overrides the base class method to perform real DSP.
        """
        if not self.is_enabled:
            return input_buffer

        if self.descriptor.category == "instrument":
            return self._generate_instrument_audio(notes, context)
        elif self.descriptor.category == "effect":
            return self._process_effect_audio(input_buffer, context)

        return input_buffer

    def _generate_instrument_audio(self, notes: List[NotePlaybackInfo],
                                   context: TransportContext) -> np.ndarray:
        """Simple sine wave synthesizer based on note playback info."""
        output = np.zeros((2, context.block_size), dtype=np.float32)

        attack_param = self._parameters.get('attack')
        attack_time = attack_param.value if attack_param else 0.01

        for note in notes:
            freq = 440.0 * (2**((note.note_pitch - 69) / 12.0))

            start_sample = note.start_sample
            num_samples_to_render = min(note.duration_samples,
                                        context.block_size - start_sample)

            if num_samples_to_render <= 0:
                continue

            t = np.arange(num_samples_to_render) / context.sample_rate
            amplitude = note.velocity / 127.0

            envelope = np.ones(num_samples_to_render)
            attack_samples = int(attack_time * context.sample_rate)
            if num_samples_to_render > attack_samples > 0:
                envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

            wave = amplitude * envelope * np.sin(2 * np.pi * freq * t)

            end_sample = start_sample + num_samples_to_render
            output[0, start_sample:end_sample] += wave
            output[1, start_sample:end_sample] += wave

        return output

    def _process_effect_audio(self, input_buffer: np.ndarray,
                              context: TransportContext) -> np.ndarray:
        """Applies a simple effect based on descriptor name."""
        if 'reverb' in self.descriptor.name.lower():
            return self._apply_simple_reverb(input_buffer)
        return input_buffer

    def _apply_simple_reverb(self, audio: np.ndarray) -> np.ndarray:
        """A placeholder for a simple reverb effect."""
        wet_param = self._parameters.get('wet')
        dry_param = self._parameters.get('dry')
        wet = wet_param.value if wet_param else 0.3
        dry = dry_param.value if dry_param else 0.7

        # This is not a real reverb, just a wet/dry mix for demonstration
        # A real implementation would use delay lines, filters, etc.
        wet_signal = audio * 0.5  # A very basic "effect"
        return (audio * dry) + (wet_signal * wet)
