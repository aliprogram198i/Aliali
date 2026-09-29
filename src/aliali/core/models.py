from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class ModuleInfo:
    key: str
    title: str
    description: str
    category: str
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
