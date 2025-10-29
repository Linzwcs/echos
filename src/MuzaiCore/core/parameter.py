# file: src/MuzaiCore/core/parameter.py
from typing import Any, List, Optional, Callable
from enum import Enum
import bisect

from ..models.parameter_model import AutomationPoint, AutomationLane, AutomationCurveType
from ..models.engine_model import TransportContext
from ..interfaces.system import IParameter, ICommand


class ParameterType(Enum):
    """参数类型枚举"""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"
    STRING = "string"


class Parameter(IParameter):
    """
    表示节点的单个可自动化参数
    支持完整的自动化、调制和值映射
    """

    def __init__(self,
                 name: str,
                 default_value: Any,
                 min_value: Optional[Any] = None,
                 max_value: Optional[Any] = None,
                 param_type: ParameterType = ParameterType.FLOAT,
                 unit: str = "",
                 display_format: str = "{:.2f}",
                 value_mapper: Optional[Callable] = None):

        self._name = name
        self._default_value = default_value
        self._base_value = default_value  # 基础值（无自动化）
        self._min_value = min_value
        self._max_value = max_value
        self._param_type = param_type
        self._unit = unit
        self._display_format = display_format
        self._value_mapper = value_mapper  # 用于非线性映射（如对数刻度）

        # 自动化数据
        self._automation_lane = AutomationLane()

        # 调制（来自LFO、包络等）
        self._modulation_amount = 0.0
        self._modulation_sources: List[str] = []  # 调制源ID列表

        # 值变化回调
        self._change_callbacks: List[Callable] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Any:
        """返回基础值（无自动化）"""
        return self._base_value

    @property
    def automation_lane(self) -> AutomationLane:
        return self._automation_lane

    @property
    def param_type(self) -> ParameterType:
        return self._param_type

    @property
    def min_value(self) -> Any:
        return self._min_value

    @property
    def max_value(self) -> Any:
        return self._max_value

    @property
    def unit(self) -> str:
        return self._unit

    def get_value_at(self, context: TransportContext) -> Any:
        """
        计算并返回参数在特定时间点的值
        考虑基础值、自动化和调制
        """
        # 1. 从基础值开始
        final_value = self._base_value

        # 2. 如果启用了自动化，从自动化lane读取
        if self._automation_lane.is_enabled and self._automation_lane.points:
            automated_value = self._interpolate_automation(
                context.current_beat)
            final_value = automated_value

        # 3. 应用调制
        if self._modulation_amount != 0.0:
            # 在真实实现中，这里会从调制源读取值
            # modulation_value = self._read_modulation_sources(context)
            # final_value += modulation_value * self._modulation_amount
            pass

        # 4. 限制在范围内
        final_value = self._clamp(final_value)

        # 5. 应用值映射（如果有）
        if self._value_mapper:
            final_value = self._value_mapper(final_value)

        return final_value

    def _interpolate_automation(self, beat: float) -> Any:
        """
        在给定beat位置插值自动化值
        支持不同的曲线类型
        """
        points = self._automation_lane.points
        if not points:
            return self._base_value

        # 按beat排序点（如果尚未排序）
        sorted_points = sorted(points, key=lambda p: p.beat)

        # 如果beat在第一个点之前
        if beat <= sorted_points[0].beat:
            return sorted_points[0].value

        # 如果beat在最后一个点之后
        if beat >= sorted_points[-1].beat:
            return sorted_points[-1].value

        # 找到beat周围的两个点
        for i in range(len(sorted_points) - 1):
            p1 = sorted_points[i]
            p2 = sorted_points[i + 1]

            if p1.beat <= beat <= p2.beat:
                # 根据曲线类型插值
                return self._interpolate_between_points(p1, p2, beat)

        return self._base_value

    def _interpolate_between_points(self, p1: AutomationPoint,
                                    p2: AutomationPoint, beat: float) -> Any:
        """在两个自动化点之间插值"""
        # 计算归一化位置（0.0到1.0）
        t = (beat - p1.beat) / (p2.beat -
                                p1.beat) if p2.beat != p1.beat else 0.0

        # 根据曲线类型应用不同的插值
        if p1.curve_type == AutomationCurveType.LINEAR:
            # 线性插值
            return p1.value + (p2.value - p1.value) * t

        elif p1.curve_type == AutomationCurveType.EXPONENTIAL:
            # 指数插值
            # 使用curve_shape控制曲线的强度
            curve = p1.curve_shape  # -1.0到1.0
            if curve > 0:
                t = t**(1 + curve * 2)  # 向外弯曲
            else:
                t = 1 - (1 - t)**(1 - curve * 2)  # 向内弯曲
            return p1.value + (p2.value - p1.value) * t

        else:
            # 默认线性
            return p1.value + (p2.value - p1.value) * t

    def _clamp(self, value: Any) -> Any:
        """将值限制在最小和最大范围内"""
        if self._min_value is not None and value < self._min_value:
            return self._min_value
        if self._max_value is not None and value > self._max_value:
            return self._max_value
        return value

    def set_owner(self, owner_node_id: str):
        """设置参数的所有者节点ID"""
        self._owner_node_id = owner_node_id

    def subscribe(self, listener: "IMixerSync"):
        """订阅参数变化事件"""
        if listener not in self._mixer_listeners:
            self._mixer_listeners.append(listener)

    def _set_value_internal(self, new_value: Any):
        old_value = self._base_value
        self._base_value = self._clamp(new_value)

        # 通知变化回调
        for callback in self._change_callbacks:
            callback(old_value, self._base_value)

        # 通知混音器监听者
        if self._owner_node_id:
            for listener in self._mixer_listeners:
                listener.on_parameter_changed(self._owner_node_id, self._name,
                                              self._base_value)

    def add_automation_point(self,
                             beat: float,
                             value: Any,
                             curve_type: str = AutomationCurveType.LINEAR,
                             curve_shape: float = 0.0):
        """在指定beat添加自动化点"""
        point = AutomationPoint(beat=beat,
                                value=self._clamp(value),
                                curve_type=curve_type,
                                curve_shape=curve_shape)
        self._automation_lane.points.append(point)
        self._automation_lane.points.sort(key=lambda p: p.beat)
        print(
            f"Added automation point to '{self._name}' at beat {beat}: {value}"
        )

    def remove_automation_point_at(self,
                                   beat: float,
                                   tolerance: float = 0.01) -> bool:
        """移除指定beat附近的自动化点"""
        for i, point in enumerate(self._automation_lane.points):
            if abs(point.beat - beat) <= tolerance:
                self._automation_lane.points.pop(i)
                print(
                    f"Removed automation point from '{self._name}' at beat {beat}"
                )
                return True
        return False

    def clear_automation(self):
        """清除所有自动化数据"""
        self._automation_lane.points.clear()
        print(f"Cleared automation for '{self._name}'")

    def enable_automation(self, enabled: bool = True):
        """启用或禁用自动化"""
        self._automation_lane.is_enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"Automation {status} for '{self._name}'")

    def add_modulation_source(self, source_id: str, amount: float = 0.5):
        """添加调制源（LFO、包络等）"""
        if source_id not in self._modulation_sources:
            self._modulation_sources.append(source_id)
            self._modulation_amount = amount
            print(
                f"Added modulation source {source_id[:8]} to '{self._name}' with amount {amount}"
            )

    def remove_modulation_source(self, source_id: str):
        """移除调制源"""
        if source_id in self._modulation_sources:
            self._modulation_sources.remove(source_id)
            print(
                f"Removed modulation source {source_id[:8]} from '{self._name}'"
            )

    def add_change_callback(self, callback: Callable):
        """添加值变化时的回调函数"""
        self._change_callbacks.append(callback)

    def create_set_value_command(self, new_value: Any) -> ICommand:
        """创建更改参数值的命令"""
        from ..core.history.commands.parameter_commands import SetParameterCommand
        return SetParameterCommand(self, new_value)

    def get_display_value(self) -> str:
        """返回格式化的显示值"""
        value = self._base_value
        if self._param_type == ParameterType.BOOL:
            return "On" if value else "Off"
        elif self._param_type == ParameterType.ENUM:
            return str(value)
        else:
            formatted = self._display_format.format(value)
            return f"{formatted} {self._unit}".strip()

    def reset_to_default(self):
        """重置为默认值"""
        self._set_value_internal(self._default_value)
        print(f"Reset '{self._name}' to default: {self._default_value}")

    def __repr__(self) -> str:
        return f"Parameter(name='{self._name}', value={self._base_value}, type={self._param_type.value})"


class ParameterGroup:
    """
    参数组，用于将相关参数组织在一起
    例如：滤波器部分、ADSR包络、振荡器等
    """

    def __init__(self, name: str):
        self.name = name
        self._parameters: List[Parameter] = []
        self._subgroups: List['ParameterGroup'] = []

    def add_parameter(self, param: Parameter):
        """添加参数到组"""
        self._parameters.append(param)

    def add_subgroup(self, group: 'ParameterGroup'):
        """添加子组"""
        self._subgroups.append(group)

    def get_all_parameters(self) -> List[Parameter]:
        """递归获取所有参数"""
        params = self._parameters.copy()
        for subgroup in self._subgroups:
            params.extend(subgroup.get_all_parameters())
        return params

    def find_parameter(self, name: str) -> Optional[Parameter]:
        """按名称查找参数"""
        for param in self._parameters:
            if param.name == name:
                return param
        for subgroup in self._subgroups:
            result = subgroup.find_parameter(name)
            if result:
                return result
        return None
