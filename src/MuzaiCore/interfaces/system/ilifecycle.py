from abc import ABC, abstractmethod
from typing import List, Optional
from .ievent_bus import IEventBus
from ...models.lifecycle_model import LifecycleState


class ILifecycleAware(ABC):

    def __init__(self):
        self._lifecycle_state = LifecycleState.CREATED
        self._event_bus: Optional['IEventBus'] = None

    @property
    def lifecycle_state(self) -> LifecycleState:
        return self._lifecycle_state

    @property
    def is_mounted(self) -> bool:
        return self._lifecycle_state == LifecycleState.MOUNTED

    @property
    def event_bus(self) -> Optional['IEventBus']:
        return self._event_bus

    def mount(self, event_bus: 'IEventBus'):
        if self._lifecycle_state == LifecycleState.MOUNTED:
            return

        if self._lifecycle_state == LifecycleState.DISPOSED:
            raise RuntimeError(
                f"{self.__class__.__name__}: Cannot mount disposed component")

        try:
            self._lifecycle_state = LifecycleState.MOUNTING
            self._event_bus = event_bus

            self._on_mount(event_bus)

            for child in self._get_children():
                if isinstance(child, ILifecycleAware):
                    print(f"mount: {child}")
                    child.mount(event_bus)

            self._lifecycle_state = LifecycleState.MOUNTED

        except Exception as e:
            self._lifecycle_state = LifecycleState.CREATED
            self._event_bus = None
            raise RuntimeError(
                f"{self.__class__.__name__}: Mount failed: {e}") from e

    def unmount(self):

        if self._lifecycle_state != LifecycleState.MOUNTED:
            return
        try:
            self._lifecycle_state = LifecycleState.UNMOUNTING

            for child in reversed(self._get_children()):
                if isinstance(child, ILifecycleAware):
                    child.unmount()

            self._on_unmount()

            self._event_bus = None
            self._lifecycle_state = LifecycleState.CREATED

        except Exception as e:
            self._event_bus = None
            self._lifecycle_state = LifecycleState.CREATED
            print(f"{self.__class__.__name__}: Unmount error: {e}")

    def dispose(self):

        self.unmount()
        self._lifecycle_state = LifecycleState.DISPOSED

    @abstractmethod
    def _on_mount(self, event_bus: 'IEventBus'):
        pass

    @abstractmethod
    def _on_unmount(self):

        pass

    @abstractmethod
    def _get_children(self) -> List['ILifecycleAware']:

        return []
