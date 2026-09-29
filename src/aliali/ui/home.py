from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Quick Scan", callback_data="menu:scan")],
        [InlineKeyboardButton("🔵 Facebook Ops", callback_data="menu:facebook"),
         InlineKeyboardButton("🌐 Network Security", callback_data="menu:network")],
        [InlineKeyboardButton("📱 Identity Intelligence", callback_data="menu:identity"),
         InlineKeyboardButton("🚨 Cases", callback_data="menu:cases")],
        [InlineKeyboardButton("📊 Reports", callback_data="menu:reports"),
         InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings")],
    ])

def home_text() -> str:
    return (
        "🛡️ *Aliali Cyber Operations*\n\n"
        "Modular security analysis and investigation workspace.\n\n"
        "🟢 Core: Operational\n"
        "🔐 Authorization-first\n"
        "🧩 Modular architecture\n\n"
        "اختر الوحدة التي تريد استخدامها:"
    )
