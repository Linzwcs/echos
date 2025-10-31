# file: src/MuzaiCore/core/parameter.py
from typing import Any, Dict, List, Optional, Callable, Tuple
from enum import Enum
import bisect

import threading
import time
from collections import defaultdict

from ..models.parameter_model import AutomationPoint, AutomationLane, AutomationCurveType
from ..models.engine_model import TransportContext
from ..models.event_model import ParameterChanged
from ..interfaces.system import IParameter, ICommand, IEventBus
from ..interfaces.system.ilifecycle import ILifecycleAware


class ParameterBatchUpdater:
    """
    参数批量更新器
    收集短时间内的参数变化，批量发布事件
    """

    def __init__(self, event_bus: 'IEventBus', flush_interval: float = 0.016):
        self._event_bus = event_bus
        self._flush_interval = flush_interval
        self._pending_changes: Dict[Tuple[str, str], Any] = {}
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._is_running = False

    def start(self):
        """启动批量更新器"""
        if self._is_running:
            return

        self._stop_flag.clear()
        self._is_running = True
        self._flush_thread = threading.Thread(target=self._flush_loop,
                                              daemon=True)
        self._flush_thread.start()

    def stop(self):
        """停止批量更新器"""
        if not self._is_running:
            return

        self._stop_flag.set()
        self._is_running = False

        if self._flush_thread:
            self._flush_thread.join(timeout=1.0)

        self.flush_now()

    def queue_change(self, node_id: str, param_name: str, new_value: Any):
        """队列化参数变化"""
        with self._lock:
            self._pending_changes[(node_id, param_name)] = new_value

    def flush_now(self):
        """立即刷新所有待处理的变化"""
        with self._lock:
            if not self._pending_changes:
                return

            changes = self._pending_changes.copy()
            self._pending_changes.clear()

        from ..models.event_model import ParameterChanged
        for (node_id, param_name), new_value in changes.items():
            self._event_bus.publish(
                ParameterChanged(owner_node_id=node_id,
                                 param_name=param_name,
                                 new_value=new_value))

    def _flush_loop(self):
        """后台刷新循环"""
        while not self._stop_flag.is_set():
            time.sleep(self._flush_interval)
            self.flush_now()


class Parameter(IParameter):
    """
    优化后的参数类
    支持批量更新和立即模式
    """

    _batch_updater: Optional[ParameterBatchUpdater] = None

    def __init__(self,
                 owner_node_id: str,
                 name: str,
                 default_value: Any,
                 min_value: Optional[Any] = None,
                 max_value: Optional[Any] = None,
                 unit: str = ""):
        super().__init__()
        self._owner_node_id = owner_node_id
        self._name = name
        self._default_value = default_value
        self._base_value = default_value
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit

        self._automation_lane = AutomationLane()
        self._immediate_mode = False
        self._change_callbacks = []

    @classmethod
    def initialize_batch_updater(cls, event_bus: 'IEventBus'):
        """初始化全局批量更新器"""
        if cls._batch_updater is None:
            cls._batch_updater = ParameterBatchUpdater(event_bus)
            cls._batch_updater.start()

    @classmethod
    def shutdown_batch_updater(cls):
        """关闭全局批量更新器"""
        if cls._batch_updater:
            cls._batch_updater.stop()
            cls._batch_updater = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Any:
        return self._base_value

    @property
    def automation_lane(self) -> AutomationLane:
        return self._automation_lane

    @property
    def max_value(self):
        return self._max_value

    @property
    def min_value(self):
        return self._min_value

    @property
    def unit(self):
        return self._unit

    def set_value(self, new_value: Any, immediate: bool = False):
        """
        设置参数值
        
        Args:
            new_value: 新值
            immediate: 是否立即发布事件
        """
        old_value = self._base_value
        clamped_value = self._clamp(new_value)

        if old_value == clamped_value:
            return

        self._base_value = clamped_value

        # 执行回调
        for callback in self._change_callbacks:
            try:
                callback(old_value, self._base_value)
            except Exception as e:
                print(f"Parameter callback error: {e}")

        # 发布事件
        if self.is_mounted:
            if immediate or self._immediate_mode:
                # 立即发布
                from ..models.event_model import ParameterChanged
                self._event_bus.publish(
                    ParameterChanged(owner_node_id=self._owner_node_id,
                                     param_name=self._name,
                                     new_value=self._base_value))
            elif self._batch_updater:
                # 批量更新
                self._batch_updater.queue_change(self._owner_node_id,
                                                 self._name, self._base_value)

    def get_value_at(self, context: TransportContext) -> Any:
        """计算在特定时间点的值（考虑自动化）"""
        if not self._automation_lane.is_enabled or not self._automation_lane.points:
            return self._base_value

        return self._interpolate_automation(context.current_beat)

    def add_automation_point(self,
                             beat: float,
                             value: Any,
                             curve_type: str = AutomationCurveType.LINEAR,
                             curve_shape: float = 0.0):
        """添加自动化点"""
        point = AutomationPoint(beat=beat,
                                value=self._clamp(value),
                                curve_type=curve_type,
                                curve_shape=curve_shape)
        self._automation_lane.points.append(point)
        self._automation_lane.points.sort(key=lambda p: p.beat)

    def remove_automation_point_at(self,
                                   beat: float,
                                   tolerance: float = 0.01) -> bool:
        """移除指定位置的自动化点"""
        for i, point in enumerate(self._automation_lane.points):
            if abs(point.beat - beat) <= tolerance:
                self._automation_lane.points.pop(i)
                return True
        return False

    def clear_automation(self):
        """清除所有自动化"""
        self._automation_lane.points.clear()

    def enable_automation(self, enabled: bool = True):
        """启用/禁用自动化"""
        self._automation_lane.is_enabled = enabled

    def enable_immediate_mode(self):
        """启用立即模式（用于Command执行）"""
        self._immediate_mode = True

    def disable_immediate_mode(self):
        """禁用立即模式"""
        self._immediate_mode = False

    def add_change_callback(self, callback: Callable):
        """添加值变化回调"""
        self._change_callbacks.append(callback)

    def reset_to_default(self):
        """重置到默认值"""
        self.set_value(self._default_value, immediate=True)

    def _clamp(self, value: Any) -> Any:
        """限制值在有效范围内"""
        if self._min_value is not None and value < self._min_value:
            return self._min_value
        if self._max_value is not None and value > self._max_value:
            return self._max_value
        return value

    def _interpolate_automation(self, beat: float) -> Any:
        """插值自动化曲线"""
        points = sorted(self._automation_lane.points, key=lambda p: p.beat)

        if not points:
            return self._base_value

        if beat <= points[0].beat:
            return points[0].value

        if beat >= points[-1].beat:
            return points[-1].value

        # 找到两个包围点
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            if p1.beat <= beat <= p2.beat:
                t = (beat - p1.beat) / (p2.beat -
                                        p1.beat) if p2.beat != p1.beat else 0.0

                if p1.curve_type == AutomationCurveType.LINEAR:
                    return p1.value + (p2.value - p1.value) * t
                elif p1.curve_type == AutomationCurveType.EXPONENTIAL:
                    curve = p1.curve_shape
                    if curve > 0:
                        t = t**(1 + curve * 2)
                    else:
                        t = 1 - (1 - t)**(1 - curve * 2)
                    return p1.value + (p2.value - p1.value) * t
                else:
                    return p1.value

        return self._base_value

    def _get_children(self) -> List[ILifecycleAware]:
        return []

    def __repr__(self) -> str:
        return f"Parameter(name='{self._name}', value={self._base_value}, type={self._param_type.value})"


class VCAParameter(Parameter):
    """
    VCA参数 - 特殊的参数类型
    """

    def __init__(self,
                 owner_node_id: str,
                 name: str,
                 default_value,
                 event_bus: Optional[IEventBus] = None,
                 min_value=None,
                 max_value=None):
        super().__init__(owner_node_id=owner_node_id,
                         name=name,
                         default_value=default_value,
                         event_bus=event_bus,
                         min_value=min_value,
                         max_value=max_value)


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
