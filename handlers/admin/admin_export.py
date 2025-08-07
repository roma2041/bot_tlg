# handlers/admin/admin_export.py
# Выгрузка заявок в Excel для администратора.

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

ADMIN_EXPORT = "ADMIN_EXPORT"

async def admin_export_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Меню экспорта заявок администратора. (Заглушка)")
    return ADMIN_EXPORT

# Здесь будут обработчики экспорта заявок в Excel
