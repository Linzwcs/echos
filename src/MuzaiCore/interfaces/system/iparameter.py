# file: src/MuzaiCore/interfaces/system/iparameter.py
from abc import ABC, abstractmethod
from typing import Any, Optional
from .ilifecycle import ILifecycleAware
from .ievent_bus import IEventBus
from ...models.parameter_model import AutomationLane
from ...models.engine_model import TransportContext


class IParameter(ILifecycleAware, ABC):
    """
    表示一个可自动化参数的完整接口。
    
    它结合了参数的静态描述（名称、范围等）和动态状态（当前值、自动化）。
    """

    # --- Static Descriptor Properties ---
    @property
    @abstractmethod
    def name(self) -> str:
        """参数的唯一名称（在其所有者节点内）。"""
        pass

    @property
    @abstractmethod
    def min_value(self) -> Optional[Any]:
        """参数的最小值。"""
        pass

    @property
    @abstractmethod
    def max_value(self) -> Optional[Any]:
        """参数的最大值。"""
        pass

    @property
    @abstractmethod
    def unit(self) -> str:
        """参数的单位（例如 'dB', '%', 'Hz'）。"""
        pass

    # --- Dynamic Value Properties & Methods ---
    @property
    @abstractmethod
    def value(self) -> Any:
        """获取参数的基础值（没有自动化或调制）。"""
        pass

    @abstractmethod
    def set_value(self, value: Any):
        """
        设置参数的基础值。
        实现类应在此方法中处理值的范围限制并发布 ParameterChanged 事件。
        """
        pass

    @abstractmethod
    def get_value_at(self, context: TransportContext) -> Any:
        """
        计算并返回在特定时间点的最终值，考虑基础值、自动化和调制。
        """
        pass

    # --- Automation Properties & Methods ---
    @property
    @abstractmethod
    def automation_lane(self) -> AutomationLane:
        """获取此参数的自动化通道数据。"""
        pass

    @abstractmethod
    def add_automation_point(self, beat: float, value: Any, curve_type: str,
                             curve_shape: float):
        """向自动化通道添加一个新点。"""
        pass

    @abstractmethod
    def remove_automation_point_at(self,
                                   beat: float,
                                   tolerance: float = 0.01) -> bool:
        """在指定的节拍位置移除一个自动化点。"""
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None
