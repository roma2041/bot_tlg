# handlers/errors.py
# Заглушка для error_handler

import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_menu import get_reply_keyboard
from config import ROLE_USER

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка в обработчике: {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            'Произошла ошибка. Пожалуйста, попробуйте снова.',
            reply_markup=get_reply_keyboard(getattr(context.user_data, 'role', ROLE_USER))
        )
