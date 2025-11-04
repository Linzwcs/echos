from abc import ABC, abstractmethod
from typing import List, Dict


class ICommand(ABC):

    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self) -> bool:
        pass

    @abstractmethod
    def can_merge_with(self, other: 'ICommand') -> bool:
        pass

    @abstractmethod
    def merge_with(self, other: 'ICommand'):
        pass

    @property
    @abstractmethod
    def description(self) -> str:
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
        pass

    @abstractmethod
    def end_macro_command(self):
        pass

    @abstractmethod
    def cancel_macro_command(self):
        pass

    @abstractmethod
    def get_undo_history(self) -> List[str]:
        pass

    @abstractmethod
    def get_redo_history(self) -> List[str]:
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, int]:
        pass

    @abstractmethod
    def can_undo(self) -> bool:
        pass

    @abstractmethod
    def can_redo(self) -> bool:
        pass
