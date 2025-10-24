# file: src/MuzaiCore/services/api_types.py
from typing import Any, NamedTuple, List, Dict, Tuple, Optional


class ToolResponse(NamedTuple):
    status: str
    data: Optional[Dict[str, Any]]
    message: str
