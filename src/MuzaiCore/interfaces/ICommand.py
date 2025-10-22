# file: src/MuzaiCore/interfaces/ICommand.py
from abc import ABC, abstractmethod
from typing import List


class ICommand(ABC):

    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self) -> bool:
        pass

    @abstractmethod
    def can_merge_with(self, other: 'ICommand') -> bool:
        """Returns True if this command can be merged with a subsequent one."""
        pass

    @abstractmethod
    def merge_with(self, other: 'ICommand'):
        """Merges the subsequent command into this one."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A user-readable description for the undo menu, e.g., 'Change Volume'."""
        pass


class ICommandManager(ABC):

    @abstractmethod
    def execute_command(self, command: ICommand):
        pass

    @abstractmethod
    def undo(self) -> None:
        pass

    @abstractmethod
    def redo(self) -> None:
        pass

    @abstractmethod
    def begin_macro_command(self, description: str):
        """Starts grouping subsequent commands into a single undo step."""
        pass

    @abstractmethod
    def end_macro_command(self):
        """Ends the grouping of a macro command."""
        pass

    @abstractmethod
    def get_undo_history(self) -> List[str]:
        """Returns a list of descriptions of commands in the undo stack."""
        pass
