from abc import ABC, abstractmethod
from typing import List
from .inode import ITrack
from .ilifecycle import ILifecycleAware
from .ievent_bus import IEventBus
from .iserializable import ISerializable
from ...models import Port, Connection


class IRouter(
        ILifecycleAware,
        ISerializable,
        ABC,
):

    @property
    def nodes(self) -> dict[str, ITrack]:
        pass

    @abstractmethod
    def add_node(self, node: ITrack):
        pass

    @abstractmethod
    def remove_node(self, node_id: str):
        pass

    @abstractmethod
    def connect(self, source_port: Port, dest_port: Port) -> bool:
        pass

    @abstractmethod
    def disconnect(self, source_port: Port, dest_port: Port) -> bool:
        pass

    @abstractmethod
    def get_processing_order(self) -> List[str]:
        pass

    @abstractmethod
    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        pass

    @abstractmethod
    def get_all_connections(self) -> List[Connection]:
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None
