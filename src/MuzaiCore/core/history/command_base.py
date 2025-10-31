from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import uuid


class CommandState:
    """命令状态枚举"""
    CREATED = "created"
    EXECUTED = "executed"
    UNDONE = "undone"
    FAILED = "failed"


class BaseCommand(ABC):
    """
    改进的Command基类
    
    特点：
    1. 内置状态跟踪
    2. 执行时间记录
    3. 错误信息保存
    4. 幂等性保证
    """

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
        """
        执行命令
        
        返回：
            True: 成功
            False: 失败
        """
        if self._state == CommandState.EXECUTED:
            print(f"Command Warning: {self.description} already executed")
            return True  # 幂等性：已执行视为成功

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
        """撤销命令"""
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
        """子类实现实际的执行逻辑"""
        pass

    @abstractmethod
    def _do_undo(self) -> bool:
        """子类实现实际的撤销逻辑"""
        pass

    def can_merge_with(self, other: 'BaseCommand') -> bool:
        """是否可以与另一个命令合并（默认不合并）"""
        return False

    def merge_with(self, other: 'BaseCommand'):
        """合并另一个命令"""
        raise NotImplementedError(
            f"{type(self).__name__} does not support merging")

    def __repr__(self) -> str:
        return f"Command(desc='{self.description}', state={self._state})"


# file: src/MuzaiCore/core/history/command_manager.py
"""
改进的CommandManager

修复：
1. 线程安全
2. 更好的宏命令支持
3. 清晰的状态管理
"""
import threading
from typing import List, Dict, Optional
from datetime import datetime

from ...interfaces.system import ICommand, ICommandManager
from .command_base import BaseCommand, CommandState


class MacroCommand(BaseCommand):
    """
    宏命令 - 组合多个命令
    
    改进：
    - 原子性执行（全成功或全失败）
    - 嵌套支持
    - 清晰的错误报告
    """

    def __init__(self, description: str):
        super().__init__(description)
        self._commands: List[BaseCommand] = []
        self._is_recording = True

    def add_command(self, command: BaseCommand):
        """添加子命令"""
        if not self._is_recording:
            raise RuntimeError("Cannot add commands to a finalized macro")
        self._commands.append(command)

    def finalize(self):
        """结束记录"""
        self._is_recording = False

    def _do_execute(self) -> bool:
        """
        原子性执行所有子命令
        
        如果任何命令失败，撤销所有已执行的命令
        """
        executed_commands = []

        for cmd in self._commands:
            if not cmd.execute():
                # 失败：撤销所有已执行的命令
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
        """按相反顺序撤销所有子命令"""
        for cmd in reversed(self._commands):
            if not cmd.undo():
                print(
                    f"MacroCommand Warning: Failed to undo {cmd.description}")
                # 继续尝试撤销其他命令
                # 在实际应用中，这里可能需要更复杂的错误处理

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
