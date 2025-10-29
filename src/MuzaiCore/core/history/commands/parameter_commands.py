# file: src/MuzaiCore/subsystems/commands/parameter_commands.py
from typing import Any
from ....interfaces.system import ICommand, IParameter


class SetParameterCommand(ICommand):
    """设置参数值的命令"""

    def __init__(self, parameter: IParameter, new_value: Any):
        self._parameter = parameter
        self._new_value = new_value
        self._old_value = parameter.value
        self._executed = False

    def execute(self) -> bool:
        """执行命令"""
        try:
            self._parameter._set_value_internal(self._new_value)
            self._executed = True
            return True
        except Exception as e:
            print(f"Failed to set parameter: {e}")
            return False

    def undo(self) -> bool:
        """撤销命令"""
        if not self._executed:
            return False

        try:
            self._parameter._set_value_internal(self._old_value)
            self._executed = False
            return True
        except Exception as e:
            print(f"Failed to undo parameter change: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        """检查是否可以合并"""
        if not isinstance(other, SetParameterCommand):
            return False

        # 只有修改同一参数的连续命令才能合并
        return (self._parameter is other._parameter and self._executed
                and not other._executed)

    def merge_with(self, other: ICommand):
        """合并命令"""
        if not self.can_merge_with(other):
            raise ValueError("Cannot merge commands")

        # 保留原始旧值，更新为新的新值
        self._new_value = other._new_value

    @property
    def description(self) -> str:
        return f"Set '{self._parameter.name}' to {self._new_value}"


class AddAutomationPointCommand(ICommand):
    """添加自动化点的命令"""

    def __init__(self, parameter: IParameter, beat: float, value: Any):
        self._parameter = parameter
        self._beat = beat
        self._value = value
        self._point_index = None

    def execute(self) -> bool:
        try:
            self._parameter.add_automation_point(self._beat, self._value)
            # 找到刚添加的点的索引
            for i, point in enumerate(self._parameter.automation_lane.points):
                if point.beat == self._beat and point.value == self._value:
                    self._point_index = i
                    break
            return True
        except Exception as e:
            print(f"Failed to add automation point: {e}")
            return False

    def undo(self) -> bool:
        if self._point_index is None:
            return False

        try:
            self._parameter.automation_lane.points.pop(self._point_index)
            return True
        except Exception as e:
            print(f"Failed to undo automation point: {e}")
            return False

    def can_merge_with(self, other: ICommand) -> bool:
        return False

    def merge_with(self, other: ICommand):
        raise NotImplementedError()

    @property
    def description(self) -> str:
        return f"Add automation point to '{self._parameter.name}' at beat {self._beat}"
