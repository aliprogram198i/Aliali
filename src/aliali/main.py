import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from .config import Settings
from .core.registry import ModuleRegistry
from .modules.facebook import FACEBOOK_MODULES
from .modules.network import NETWORK_MODULES
from .ui.home import home_keyboard, home_text

logging.basicConfig(level=logging.INFO)
registry = ModuleRegistry()
for module in [*FACEBOOK_MODULES, *NETWORK_MODULES]:
    registry.register(module)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(home_text(), reply_markup=home_keyboard(), parse_mode="Markdown")

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    await query.edit_message_text(
        f"🧩 *Module:* `{query.data}`\n\n"
        "هذه الواجهة جاهزة للربط بالـmodule المناسب.\n"
        "سيتم تنفيذ الوظائف الفعلية فقط ضمن نطاق مصرح به.",
        parse_mode="Markdown",
        reply_markup=home_keyboard(),
    )

def build_application(settings: Settings) -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    return app

def main() -> None:
    settings = Settings()
    build_application(settings).run_polling()
