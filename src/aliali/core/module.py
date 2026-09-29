from abc import ABC, abstractmethod
from typing import Any

class SecurityModule(ABC):
    key: str
    title: str

    @abstractmethod
    async def run(self, target: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a module within an explicitly authorized scope."""
        raise NotImplementedError
