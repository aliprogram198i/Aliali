from aliali.core.models import ModuleInfo
from aliali.core.registry import ModuleRegistry


def test_registry_register_and_lookup():
    registry = ModuleRegistry()
    module = ModuleInfo("test.module", "Test", "Test module", "test")
    registry.register(module)
    assert registry.get("test.module") == module


def test_registry_rejects_duplicate_keys():
    registry = ModuleRegistry()
    module = ModuleInfo("test.module", "Test", "Test module", "test")
    registry.register(module)
    try:
        registry.register(module)
        assert False, "duplicate registration must fail"
    except ValueError:
        pass
