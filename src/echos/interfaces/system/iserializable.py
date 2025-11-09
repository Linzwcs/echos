from abc import ABC, abstractmethod
from typing import TypeVar, Type, Any
from ...models.state_model.base_state import BaseState

S = TypeVar('S', bound=BaseState)
T = TypeVar('T', bound='ISerializable')


class ISerializable(ABC):

    @abstractmethod
    def to_state(self) -> S:
        pass

    @classmethod
    @abstractmethod
    def from_state(cls: Type[T], state: S, **kwargs: Any) -> T:
        pass
