from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ToolResponse:
    status: str
    data: Optional[Dict[str, Any]]
    message: str
