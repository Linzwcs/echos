# file: src/MuzaiCore/interfaces/system/iparameter.py
from abc import ABC, abstractmethod
from typing import Any, Optional
from .ilifecycle import ILifecycleAware
from ...models.parameter_model import AutomationLane
from ...models.engine_model import TransportContext


class IParameter(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def min_value(self) -> Optional[Any]:
        pass

    @property
    @abstractmethod
    def max_value(self) -> Optional[Any]:
        pass

    @property
    @abstractmethod
    def unit(self) -> str:
        pass

    @property
    @abstractmethod
    def value(self) -> Any:
        pass

    @abstractmethod
    def set_value(self, value: Any):
        pass

    @abstractmethod
    def get_value_at(self, context: TransportContext) -> Any:
        pass

    @property
    @abstractmethod
    def automation_lane(self) -> AutomationLane:
        pass

    @abstractmethod
    def add_automation_point(
        self,
        beat: float,
        value: Any,
        curve_type: str,
        curve_shape: float,
    ):
        pass

    @abstractmethod
    def remove_automation_point_at(
        self,
        beat: float,
        tolerance: float = 0.01,
    ) -> bool:
        pass
