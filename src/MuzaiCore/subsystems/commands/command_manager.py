# file: src/MuzaiCore/subsystems/commands/command_manager.py
from typing import List
from ...interfaces import ICommand, ICommandManager


class CommandManager(ICommandManager):
    """A simple implementation of a command manager for undo/redo history."""

    def __init__(self):
        self._undo_stack: List[ICommand] = []
        self._redo_stack: List[ICommand] = []

    def execute_command(self, command: ICommand):
        if command.execute():
            self._undo_stack.append(command)
            # Executing a new command clears the redo stack
            self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            print("Undo stack is empty.")
            return

        command_to_undo = self._undo_stack.pop()
        if command_to_undo.undo():
            self._redo_stack.append(command_to_undo)

    def redo(self):
        if not self._redo_stack:
            print("Redo stack is empty.")
            return

        command_to_redo = self._redo_stack.pop()
        if command_to_redo.execute():
            self._undo_stack.append(command_to_redo)
