from typing import Optional
from ..interfaces.system import IEngineController, IEngine, IEventBus, IDomainTimeline, IRouter


class EngineController(IEngineController):

    def __init__(self, router: IRouter, timeline: IDomainTimeline):
        super().__init__()
        self._audio_engine = None
        self._router = router
        self._timeline = timeline

    @property
    def engine(self) -> Optional[IEngine]:
        return self._audio_engine

    def attach_engine(self, engine: IEngine) -> bool:

        if not self.is_mounted:
            raise RuntimeError(
                "Project must be initialized before attaching engine")

        if self._audio_engine:
            print("Project: Replacing existing engine")
            self.detach_engine()

        self._audio_engine = engine
        engine.mount(self._event_bus)

        from ..models.event_model import ProjectLoaded
        self._event_bus.publish(
            ProjectLoaded(timeline_state=self._timeline.timeline_state))

    def detach_engine(self) -> bool:
        if not self._audio_engine:
            return

        from ..models.event_model import ProjectClosed
        self._event_bus.publish(ProjectClosed())

        self._audio_engine.unmount()
        self._audio_engine = None
        print(f"Project '{self._name}': ✓ Engine detached")

    def play(self):
        self._audio_engine.play()

    def stop(self):
        self._audio_engine.stop()

    def pause(self):
        self._audio_engine.pause()

    def seek(self, beat: float):
        self._audio_engine.seek(beat=beat)

    @property
    def is_playing(self) -> bool:
        """Returns True if the engine is currently playing."""
        pass

    @property
    def current_beat(self) -> float:
        """Gets the current playback position in beats."""
        pass

    def _get_children(self):
        return []

    def _on_mount(self, bus: IEventBus):
        self._event_bus = bus

    def _on_unmount(self):
        self._event_bus = None
