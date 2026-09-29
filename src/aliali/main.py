import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from .config import Settings
from .core.registry import ModuleRegistry
from .modules.facebook import FACEBOOK_MODULES
from .modules.network import NETWORK_MODULES
from .ui.home import home_keyboard, home_text
from .ui.menus import category_text, module_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

registry = ModuleRegistry()
for module in [*FACEBOOK_MODULES, *NETWORK_MODULES]:
    registry.register(module)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            home_text(),
            reply_markup=home_keyboard(),
            parse_mode="Markdown",
        )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    action, _, value = query.data.partition(":")

    if action == "menu" and value in {"facebook", "network"}:
        title = "Facebook Operations" if value == "facebook" else "Network Security"
        modules = registry.list_by_category(value)
        await query.edit_message_text(
            category_text(title, modules),
            reply_markup=module_keyboard(modules),
            parse_mode="Markdown",
        )
        return

    if action == "module":
        module = registry.get(value)
        if module is None or not module.enabled:
            await query.edit_message_text(
                "⚠️ هذه الوحدة غير متاحة حاليًا.",
                reply_markup=home_keyboard(),
            )
            return

        await query.edit_message_text(
            f"🧩 *{module.title}*\n\n"
            f"{module.description}\n\n"
            "هذه نقطة الدخول الرسمية للوحدة. لا يتم تنفيذ عمليات "
            "حساسة قبل التحقق من نطاق التفويض.",
            reply_markup=home_keyboard(),
            parse_mode="Markdown",
        )
        return

    await query.edit_message_text(
        "🏠 *Aliali Cyber Operations*\n\nاختر طبقة:",
        reply_markup=home_keyboard(),
        parse_mode="Markdown",
    )


def build_application(settings: Settings) -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    return app


def main() -> None:
    settings = Settings()
    build_application(settings).run_polling()
