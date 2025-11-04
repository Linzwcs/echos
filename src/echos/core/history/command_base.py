from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import uuid


class CommandState:
    CREATED = "created"
    EXECUTED = "executed"
    UNDONE = "undone"
    FAILED = "failed"


class BaseCommand(ABC):

    def __init__(self, description: str):
        self._command_id = str(uuid.uuid4())
        self._description = description
        self._state = CommandState.CREATED
        self._executed_at: Optional[datetime] = None
        self._undone_at: Optional[datetime] = None
        self._error: Optional[str] = None

    @property
    def command_id(self) -> str:
        return self._command_id

    @property
    def description(self) -> str:
        return self._description

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_executed(self) -> bool:
        return self._state == CommandState.EXECUTED

    @property
    def error(self) -> Optional[str]:
        return self._error

    def execute(self) -> bool:

        if self._state == CommandState.EXECUTED:
            print(f"Command Warning: {self.description} already executed")
            return True

        try:
            result = self._do_execute()
            if result:
                self._state = CommandState.EXECUTED
                self._executed_at = datetime.now()
                print(f"Command: ✓ {self.description}")
            else:
                self._state = CommandState.FAILED
                self._error = "Execution returned False"
                print(f"Command: ✗ {self.description} failed")
            return result
        except Exception as e:
            self._state = CommandState.FAILED
            self._error = str(e)
            print(f"Command: ✗ {self.description} raised exception: {e}")
            return False

    def undo(self) -> bool:

        if self._state != CommandState.EXECUTED:
            print(
                f"Command Warning: Cannot undo {self.description} (state: {self._state})"
            )
            return False

        try:
            result = self._do_undo()
            if result:
                self._state = CommandState.UNDONE
                self._undone_at = datetime.now()
                print(f"Command: ↶ Undone {self.description}")
            else:
                self._error = "Undo returned False"
                print(f"Command: ✗ Failed to undo {self.description}")
            return result
        except Exception as e:
            self._error = str(e)
            print(f"Command: ✗ Undo raised exception: {e}")
            return False

    @abstractmethod
    def _do_execute(self) -> bool:

        pass

    @abstractmethod
    def _do_undo(self) -> bool:

        pass

    def can_merge_with(self, other: 'BaseCommand') -> bool:

        return False

    def merge_with(self, other: 'BaseCommand'):

        raise NotImplementedError(
            f"{type(self).__name__} does not support merging")

    def __repr__(self) -> str:
        return f"Command(desc='{self.description}', state={self._state})"
