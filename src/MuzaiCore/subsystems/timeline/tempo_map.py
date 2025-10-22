# file: src/MuzaiCore/subsystems/timeline/tempo_map.py


class TempoMap:
    """A simplified tempo map that assumes a constant tempo for now."""

    def __init__(self, initial_tempo: float = 120.0):
        self._tempo = initial_tempo

    def set_constant_tempo(self, bpm: float):
        if bpm <= 0:
            raise ValueError("BPM must be positive.")
        self._tempo = bpm

    def beats_to_seconds(self, beats: float) -> float:
        return (beats * 60.0) / self._tempo

    def seconds_to_beats(self, seconds: float) -> float:
        return (seconds * self._tempo) / 60.0
