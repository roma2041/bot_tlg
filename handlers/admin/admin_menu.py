# handlers/admin/admin_menu.py
# Обработчики главного меню администратора и переходов между разделами.

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from keyboards.admin.menu import get_admin_main_menu, get_admin_manage_menu
from handlers.admin.states import ADMIN_MAIN, ADMIN_MANAGE, ADMIN_USERS

async def admin_main_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если нажата кнопка "Администрирование", открываем подменю
    text = update.message.text if update.message else None
    if text == "Администрирование":
        await update.message.reply_text(
            "Меню администрирования:",
            reply_markup=get_admin_manage_menu()
        )
        return ADMIN_MANAGE
    # Иначе показываем главное меню
    await update.message.reply_text(
        "Главное меню администратора:",
        reply_markup=get_admin_main_menu()
    )
    return ADMIN_MAIN

async def admin_manage_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text if update.message else None
    if text == "Управление пользователями":
        # Переход к обработчику admin_users_entry, меню формируется там
        from handlers.admin.admin_users import admin_users_entry
        return await admin_users_entry(update, context)
    # Если нажата "Назад", возвращаемся в главное меню
    if text == "↩️ Назад":
        await update.message.reply_text(
            "Главное меню администратора:",
            reply_markup=get_admin_main_menu()
        )
        return ADMIN_MAIN
    await update.message.reply_text(
        "Меню администрирования:",
        reply_markup=get_admin_manage_menu()
    )
    return ADMIN_MANAGE
