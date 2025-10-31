# file: src/MuzaiCore/core/event_bus.py
"""
A simple, in-memory domain event bus.
"""
from collections import defaultdict
from typing import Callable, List, Dict, Type, Any, TypeVar
from ..interfaces.system.ievent_bus import IEventBus
from ..models.event_model import BaseEvent


class EventBus(IEventBus):
    """
    中心化的事件总线
    
    职责：
    1. 接收领域事件
    2. 分发给注册的处理器
    3. 仅此而已（不做任何业务逻辑）
    """

    def __init__(self):
        self._subscribers: Dict[Type[BaseEvent],
                                List[Callable]] = defaultdict(list)
        print("EventBus: Initialized.")

    def subscribe(self, event_type: Type[BaseEvent], handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型（或BaseEvent表示监听所有）
            handler: 处理函数 (event: BaseEvent) -> None
        """
        self._subscribers[event_type].append(handler)
        print(
            f"EventBus: Handler '{handler.__name__}' subscribed to '{event_type.__name__}'"
        )

    def unsubscribe(self, event_type: Type[BaseEvent], handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                print(
                    f"EventBus: Handler '{handler.__name__}' unsubscribed from '{event_type.__name__}'"
                )
            except ValueError:
                pass

    def publish(self, event: BaseEvent):
        """
        发布事件
        
        Args:
            event: 事件实例
        """
        event_type = type(event)

        # 通知该类型的订阅者
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(
                        f"EventBus Error: Handler '{handler.__name__}' failed for {event_type.__name__}: {e}"
                    )

        # 通知BaseEvent的订阅者（监听所有事件）
        if BaseEvent in self._subscribers and event_type != BaseEvent:
            for handler in self._subscribers[BaseEvent]:
                try:
                    handler(event)
                except Exception as e:
                    print(
                        f"EventBus Error: Catch-all handler '{handler.__name__}' failed: {e}"
                    )

    def clear(self):
        """清空所有订阅（用于测试或清理）"""
        self._subscribers.clear()
        print("EventBus: All subscriptions cleared.")
