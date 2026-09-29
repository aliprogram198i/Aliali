from aliali.core.models import ModuleInfo
from aliali.ui.menus import category_text, module_keyboard


def test_category_text_contains_all_modules():
    modules = [
        ModuleInfo("a", "A", "First", "test"),
        ModuleInfo("b", "B", "Second", "test"),
    ]
    text = category_text("Test", modules)
    assert "A" in text
    assert "B" in text


def test_module_keyboard_uses_stable_callback_keys():
    modules = [ModuleInfo("network.asset_discovery", "Assets", "Discovery", "network")]
    keyboard = module_keyboard(modules)
    assert keyboard.inline_keyboard[0][0].callback_data == "module:network.asset_discovery"
