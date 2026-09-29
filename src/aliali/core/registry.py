from .models import ModuleInfo


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleInfo] = {}

    def register(self, module: ModuleInfo) -> None:
        if module.key in self._modules:
            raise ValueError(f"Duplicate module key: {module.key}")
        self._modules[module.key] = module

    def get(self, key: str) -> ModuleInfo | None:
        return self._modules.get(key)

    def list_by_category(self, category: str) -> list[ModuleInfo]:
        return [m for m in self._modules.values() if m.category == category and m.enabled]

    def all(self) -> list[ModuleInfo]:
        return list(self._modules.values())
