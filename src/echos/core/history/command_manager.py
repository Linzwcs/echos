import threading
from typing import List, Dict, Optional
from .command_base import BaseCommand
from ...interfaces.system import ICommandManager


class MacroCommand(BaseCommand):

    def __init__(self, description: str):
        super().__init__(description)
        self._commands: List[BaseCommand] = []
        self._is_recording = True

    def add_command(self, command: BaseCommand):

        if not self._is_recording:
            raise RuntimeError("Cannot add commands to a finalized macro")
        self._commands.append(command)

    def finalize(self):

        self._is_recording = False

    def _do_execute(self) -> bool:

        executed_commands = []

        for cmd in self._commands:
            if not cmd.execute():

                print(
                    f"MacroCommand: Aborting due to failed command: {cmd.description}"
                )
                for executed_cmd in reversed(executed_commands):
                    executed_cmd.undo()
                return False
            executed_commands.append(cmd)

        print(f"MacroCommand: ✓ All {len(self._commands)} commands executed")
        return True

    def _do_undo(self) -> bool:

        for cmd in reversed(self._commands):
            if not cmd.undo():
                print(
                    f"MacroCommand Warning: Failed to undo {cmd.description}")

        print(f"MacroCommand: ↶ Undone macro '{self.description}'")
        return True


class CommandManager(ICommandManager):
    """
    改进的命令管理器
    
    特点：
    1. 线程安全
    2. 完整的宏命令支持
    3. 统计和调试功能
    4. 历史限制
    """

    def __init__(self, max_history: int = 100):
        self._lock = threading.RLock()  # 可重入锁
        self._undo_stack: List[BaseCommand] = []
        self._redo_stack: List[BaseCommand] = []
        self._max_history = max_history

        # 宏命令支持
        self._current_macro: Optional[MacroCommand] = None
        self._macro_stack: List[MacroCommand] = []  # 嵌套宏

        # 统计
        self._total_executed = 0
        self._total_undone = 0
        self._total_redone = 0
        self._merge_count = 0

        print(f"CommandManager: Initialized (max_history={max_history})")

    def execute_command(self, command: BaseCommand):
        """
        执行命令
        
        改进：
        - 线程安全
        - 自动命令合并
        - 宏命令支持
        """
        with self._lock:
            # 如果在宏中，添加到宏而不是直接执行
            if self._current_macro:
                self._current_macro.add_command(command)
                # 立即执行（为了保持状态一致）
                if not command.execute():
                    print(
                        f"CommandManager: Command failed in macro: {command.description}"
                    )
                return

            # 尝试与上一个命令合并
            if self._undo_stack and self._undo_stack[-1].can_merge_with(
                    command):
                try:
                    self._undo_stack[-1].merge_with(command)
                    self._merge_count += 1
                    print(
                        f"CommandManager: Merged command: {command.description}"
                    )
                    return
                except Exception as e:
                    print(
                        f"CommandManager: Merge failed: {e}, executing separately"
                    )

            # 执行命令
            if command.execute():
                self._undo_stack.append(command)
                self._redo_stack.clear()  # 清空重做栈
                self._total_executed += 1

                # 限制历史大小
                if len(self._undo_stack) > self._max_history:
                    removed = self._undo_stack.pop(0)
                    print(
                        f"CommandManager: History limit reached, removed: {removed.description}"
                    )

    def undo(self) -> None:
        """撤销最后一个命令"""
        with self._lock:
            if not self._undo_stack:
                print("CommandManager: Nothing to undo")
                return

            if self._current_macro:
                print("CommandManager: Cannot undo while recording a macro")
                return

            command = self._undo_stack.pop()
            if command.undo():
                self._redo_stack.append(command)
                self._total_undone += 1
                print(f"CommandManager: ↶ Undone: {command.description}")
            else:
                # 撤销失败，放回栈中
                self._undo_stack.append(command)
                print(
                    f"CommandManager: ✗ Failed to undo: {command.description}")

    def redo(self) -> None:
        """重做最后撤销的命令"""
        with self._lock:
            if not self._redo_stack:
                print("CommandManager: Nothing to redo")
                return

            if self._current_macro:
                print("CommandManager: Cannot redo while recording a macro")
                return

            command = self._redo_stack.pop()
            if command.execute():
                self._undo_stack.append(command)
                self._total_redone += 1
                print(f"CommandManager: ↷ Redone: {command.description}")
            else:
                # 重做失败，放回栈中
                self._redo_stack.append(command)
                print(
                    f"CommandManager: ✗ Failed to redo: {command.description}")

    def begin_macro_command(self, description: str):
        """开始记录宏命令"""
        with self._lock:
            new_macro = MacroCommand(description)

            # 支持嵌套
            if self._current_macro:
                self._macro_stack.append(self._current_macro)

            self._current_macro = new_macro
            print(f"CommandManager: Started macro: '{description}'")

    def end_macro_command(self):
        """结束宏命令记录"""
        with self._lock:
            if not self._current_macro:
                print("CommandManager: No macro in progress")
                return

            macro = self._current_macro
            macro.finalize()

            # 恢复父宏或提交到历史
            if self._macro_stack:
                parent_macro = self._macro_stack.pop()
                parent_macro.add_command(macro)
                self._current_macro = parent_macro
                print(
                    f"CommandManager: Nested macro '{macro.description}' added to parent"
                )
            else:
                # 顶层宏，添加到历史
                self._current_macro = None
                self._undo_stack.append(macro)
                self._redo_stack.clear()
                print(
                    f"CommandManager: ✓ Macro completed: '{macro.description}'"
                )

    def cancel_macro_command(self):
        """取消并撤销当前宏命令"""
        with self._lock:
            if not self._current_macro:
                print("CommandManager: No macro to cancel")
                return

            macro = self._current_macro
            macro.undo()  # 撤销所有在宏中执行的命令

            # 恢复父宏
            if self._macro_stack:
                self._current_macro = self._macro_stack.pop()
            else:
                self._current_macro = None

            print(f"CommandManager: ✗ Macro cancelled: '{macro.description}'")

    def get_undo_history(self) -> List[str]:
        """获取撤销历史"""
        with self._lock:
            return [cmd.description for cmd in self._undo_stack]

    def get_redo_history(self) -> List[str]:
        """获取重做历史"""
        with self._lock:
            return [cmd.description for cmd in self._redo_stack]

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_executed": self._total_executed,
                "total_undone": self._total_undone,
                "total_redone": self._total_redone,
                "merged_commands": self._merge_count,
                "undo_stack_size": len(self._undo_stack),
                "redo_stack_size": len(self._redo_stack),
                "in_macro": self._current_macro is not None,
            }

    def can_undo(self) -> bool:
        """是否可以撤销"""
        with self._lock:
            return len(self._undo_stack) > 0 and not self._current_macro

    def can_redo(self) -> bool:
        """是否可以重做"""
        with self._lock:
            return len(self._redo_stack) > 0 and not self._current_macro

    def clear(self):
        """清空所有历史"""
        with self._lock:
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._current_macro = None
            self._macro_stack.clear()
            print("CommandManager: All history cleared")

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"CommandManager("
                f"undo={stats['undo_stack_size']}, "
                f"redo={stats['redo_stack_size']}, "
                f"in_macro={stats['in_macro']})")
