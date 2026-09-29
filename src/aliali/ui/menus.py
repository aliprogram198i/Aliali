from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from aliali.core.models import ModuleInfo


def module_keyboard(modules: list[ModuleInfo], back: str = "home") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(module.title, callback_data=f"module:{module.key}")]
        for module in modules
    ]
    rows.append([InlineKeyboardButton("◀️ Back", callback_data=back)])
    return InlineKeyboardMarkup(rows)


def category_text(title: str, modules: list[ModuleInfo]) -> str:
    lines = [f"🛡️ *{title}*", "", "اختر الوحدة:"]
    lines.extend(f"• {module.title} — {module.description}" for module in modules)
    return "\n".join(lines)
