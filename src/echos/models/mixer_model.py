from dataclasses import dataclass


@dataclass
class Send:
    """表示从一个通道到总线的发送 (纯数据模型)"""
    send_id: str
    target_bus_node_id: str
    level: "IParameter"
    is_post_fader: bool = True
    is_enabled: bool = True
