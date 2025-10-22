# file: src/MuzaiCore/subsystems/timeline/timeline.py
from ...interfaces import ITimeline
from .tempo_map import TempoMap


class Timeline(ITimeline):
    """
    Manages the conversion between time units (samples, seconds, beats).
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.tempo_map = TempoMap()

    def set_tempo(self, bpm: float):
        # For V1.0, we assume a constant tempo.
        self.tempo_map.set_constant_tempo(bpm)

    def samples_to_beats(self, sample_position: int) -> float:
        seconds = sample_position / self.sample_rate
        return self.tempo_map.seconds_to_beats(seconds)

    def beats_to_samples(self, beat_position: float) -> int:
        seconds = self.tempo_map.beats_to_seconds(beat_position)
        return int(seconds * self.sample_rate)
