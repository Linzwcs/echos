from dataclasses import dataclass


@dataclass
class Send:

    send_id: str
    target_bus_node_id: str
    level: "IParameter"
    is_post_fader: bool = True
    is_enabled: bool = True
