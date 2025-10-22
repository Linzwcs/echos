# file: src/MuzaiCore/core/parameter.py
from typing import Any, List
from ..interfaces import IParameter, ICommand
from ..models.parameter_model import AutomationPoint


# Forward declaration for type hinting
class SetParameterCommand:
    pass


class Parameter(IParameter):
    """Represents a single, automatable parameter of a node."""

    def __init__(self, name: str, value: Any):
        self._name = name
        self._value = value
        self.automation_points: List[AutomationPoint] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Any:
        # In a real engine, this would calculate the value based on automation
        # at the current playback time. Here, we return the base value.
        return self._value

    def _set_value_internal(self, new_value: Any):
        """Internal method to set the value, used by the Command."""
        self._value = new_value

    def create_set_value_command(self, new_value: Any) -> ICommand:
        """Creates a command to change the parameter's value."""
        from ..subsystems.commands.parameter_commands import SetParameterCommand
        return SetParameterCommand(self, new_value)
