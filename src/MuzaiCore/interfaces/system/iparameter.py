# file: src/MuzaiCore/interfaces/IParameter.py
from abc import ABC, abstractmethod
from typing import Any, List
from .icommand import ICommand
from ...models.parameter_model import AutomationLane  # <-- New model
from ...models.engine_model import TransportContext  # <-- For time-aware value calculation
from .isync import IMixerSync


class IParameter(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def value(self) -> Any:
        """Returns the base, non-automated value of the parameter."""
        pass

    @property
    @abstractmethod
    def automation_lane(self) -> AutomationLane:
        """The dedicated lane for this parameter's automation data."""
        pass

    # +++ NEW METHOD for real-time value calculation +++
    @abstractmethod
    def get_value_at(self, context: TransportContext) -> Any:
        """
        Calculates and returns the parameter's value at a specific point in time,
        considering both the base value and any automation.
        """
        pass

    @abstractmethod
    def create_set_value_command(self, new_value: Any) -> ICommand:
        """Returns a command object to change the base value."""
        pass

    @abstractmethod
    def subscribe(self, listener: IMixerSync):
        pass
