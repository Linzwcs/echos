# file: src/MuzaiCore/subsystems/commands/parameter_commands.py
from typing import Any
from ...interfaces import ICommand, IParameter


class SetParameterCommand(ICommand):

    def __init__(self, parameter: IParameter, new_value: Any):
        self._parameter = parameter
        self._new_value = new_value
        self._old_value = parameter.value

    def execute(self) -> bool:
        # In a real system, the parameter would have an internal setter.
        # This uses a private method as a stand-in for that concept.
        self._parameter._set_value_internal(self._new_value)
        print(
            f"Executed: Set param '{self._parameter.name}' to {self._new_value}"
        )
        return True

    def undo(self) -> bool:
        self._parameter._set_value_internal(self._old_value)
        print(
            f"Undone: Reset param '{self._parameter.name}' to {self._old_value}"
        )
        return True
