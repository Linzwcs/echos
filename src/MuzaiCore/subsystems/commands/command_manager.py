# file: src/MuzaiCore/subsystems/commands/command_manager.py
from typing import Dict, List, Optional
from datetime import datetime

from ...interfaces import ICommand, ICommandManager


class MacroCommand(ICommand):
    """
    宏命令 - 将多个命令组合成单个可撤销操作
    用于复杂的多步骤操作
    """

    def __init__(self, description: str):
        self._description = description
        self._commands: List[ICommand] = []
        self._executed = False

    def add_command(self, command: ICommand):
        """添加子命令"""
        if self._executed:
            raise RuntimeError("Cannot add commands to an executed macro")
        self._commands.append(command)

    def execute(self) -> bool:
        """按顺序执行所有子命令"""
        if self._executed:
            return False

        executed_commands = []
        try:
            for cmd in self._commands:
                if not cmd.execute():
                    # 如果任何命令失败，撤销所有已执行的命令
                    for executed_cmd in reversed(executed_commands):
                        executed_cmd.undo()
                    return False
                executed_commands.append(cmd)

            self._executed = True
            print(f"MacroCommand executed: {self._description}")
            return True
        except Exception as e:
            # 出错时撤销
            for executed_cmd in reversed(executed_commands):
                executed_cmd.undo()
            print(f"MacroCommand failed: {e}")
            return False

    def undo(self) -> bool:
        """按相反顺序撤销所有子命令"""
        if not self._executed:
            return False

        try:
            for cmd in reversed(self._commands):
                if not cmd.undo():
                    return False

            self._executed = False
            print(f"MacroCommand undone: {self._description}")
            return True
        except Exception as e:
            print(f"MacroCommand undo failed: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        """宏命令通常不合并"""
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError("MacroCommand does not support merging")

    @property
    def description(self) -> str:
        return self._description


class CommandManager(ICommandManager):
    """
    专业级命令管理器
    支持：撤销/重做、宏命令、命令合并、历史限制
    """

    def __init__(self, max_history: int = 100):
        self._undo_stack: List[ICommand] = []
        self._redo_stack: List[ICommand] = []
        self._max_history = max_history

        # 宏命令支持
        self._current_macro: Optional[MacroCommand] = None
        self._macro_stack: List[MacroCommand] = []  # 支持嵌套宏

        # 统计信息
        self._command_count = 0
        self._merge_count = 0

    def execute_command(self, command: ICommand):
        """
        执行命令并添加到撤销栈
        支持命令合并和宏命令
        """
        # 如果在宏中，添加到当前宏而不是直接执行
        if self._current_macro:
            self._current_macro.add_command(command)
            # 在宏内部立即执行
            if not command.execute():
                print(f"Command failed in macro: {command.description}")
            return

        # 尝试与上一个命令合并
        if self._undo_stack and self._undo_stack[-1].can_merge_with(command):
            print(f"Merging command with previous: {command.description}")
            self._undo_stack[-1].merge_with(command)
            self._merge_count += 1
            return

        # 执行命令
        if command.execute():
            self._undo_stack.append(command)
            self._redo_stack.clear()  # 执行新命令清空重做栈
            self._command_count += 1

            # 限制历史大小
            if len(self._undo_stack) > self._max_history:
                removed = self._undo_stack.pop(0)
                print(
                    f"History limit reached, removed oldest command: {removed.description}"
                )
        else:
            print(f"Command execution failed: {command.description}")

    def undo(self) -> None:
        """撤销最后一个命令"""
        if not self._undo_stack:
            print("Undo stack is empty - nothing to undo")
            return

        if self._current_macro:
            print("Cannot undo while recording a macro")
            return

        command_to_undo = self._undo_stack.pop()
        if command_to_undo.undo():
            self._redo_stack.append(command_to_undo)
            print(f"Undone: {command_to_undo.description}")
        else:
            # 如果撤销失败，放回栈中
            self._undo_stack.append(command_to_undo)
            print(f"Failed to undo: {command_to_undo.description}")

    def redo(self) -> None:
        """重做最后撤销的命令"""
        if not self._redo_stack:
            print("Redo stack is empty - nothing to redo")
            return

        if self._current_macro:
            print("Cannot redo while recording a macro")
            return

        command_to_redo = self._redo_stack.pop()
        if command_to_redo.execute():
            self._undo_stack.append(command_to_redo)
            print(f"Redone: {command_to_redo.description}")
        else:
            # 如果重做失败，放回栈中
            self._redo_stack.append(command_to_redo)
            print(f"Failed to redo: {command_to_redo.description}")

    def begin_macro_command(self, description: str):
        """
        开始记录宏命令
        支持嵌套宏
        """
        new_macro = MacroCommand(description)

        # 如果已经在宏中，添加到父宏
        if self._current_macro:
            self._macro_stack.append(self._current_macro)

        self._current_macro = new_macro
        print(f"Started macro: {description}")

    def end_macro_command(self):
        """
        结束宏命令记录并执行
        """
        if not self._current_macro:
            print("No macro command in progress")
            return

        macro = self._current_macro

        # 恢复父宏（如果有）
        if self._macro_stack:
            self._current_macro = self._macro_stack.pop()
            # 将完成的宏添加到父宏
            self._current_macro.add_command(macro)
        else:
            self._current_macro = None
            # 这是顶层宏，添加到撤销栈
            self._undo_stack.append(macro)
            self._redo_stack.clear()
            print(f"Completed macro: {macro.description}")

    def cancel_macro_command(self):
        """
        取消当前宏命令记录
        撤销所有在宏中执行的命令
        """
        if not self._current_macro:
            print("No macro command in progress")
            return

        # 撤销宏中的所有命令
        self._current_macro.undo()

        # 恢复父宏（如果有）
        if self._macro_stack:
            self._current_macro = self._macro_stack.pop()
        else:
            self._current_macro = None

        print("Macro command cancelled and undone")

    def get_undo_history(self) -> List[str]:
        """返回撤销栈中命令的描述列表"""
        return [cmd.description for cmd in self._undo_stack]

    def get_redo_history(self) -> List[str]:
        """返回重做栈中命令的描述列表"""
        return [cmd.description for cmd in self._redo_stack]

    def get_statistics(self) -> Dict[str, int]:
        """返回命令管理器的统计信息"""
        return {
            "total_commands": self._command_count,
            "merged_commands": self._merge_count,
            "undo_stack_size": len(self._undo_stack),
            "redo_stack_size": len(self._redo_stack),
        }

    def can_undo(self) -> bool:
        """是否可以撤销"""
        return len(self._undo_stack) > 0 and not self._current_macro

    def can_redo(self) -> bool:
        """是否可以重做"""
        return len(self._redo_stack) > 0 and not self._current_macro
