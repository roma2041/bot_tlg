# handlers/admin/admin_users.py
# Управление пользователями и ролями администратора.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from db import Database
from config import ROLE_USER, ROLE_ADMIN, ROLE_OPERATOR
from handlers.admin.states import ADMIN_USER_ID, ADMIN_USER_ACTION, ADMIN_ROLE_SELECT, ADMIN_MAIN
from keyboards.admin.menu import get_admin_main_menu  # Импорт правильной функции

async def admin_users_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ID пользователя для управления:")
    return ADMIN_USER_ID

async def admin_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text.strip()
    user_info = Database.get_user_info(user_id)
    context.user_data['manage_user_id'] = user_id
    context.user_data['manage_user_info'] = user_info
    text = f"Пользователь: {user_info['username']}\nРоль: {user_info['role']}\nСтатус: {'Заблокирован' if user_info.get('blocked') else 'Активен'}"
    keyboard = [
        [InlineKeyboardButton("👥 Назначить роль", callback_data="set_role")],
        [InlineKeyboardButton("🖕🏻 Заблокировать", callback_data="block")],
        [InlineKeyboardButton("🫶🏻 Разблокировать", callback_data="unblock")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_USER_ACTION

async def admin_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = context.user_data['manage_user_id']
    user_info = context.user_data['manage_user_info']
    if data == "set_role":
        role = user_info['role']
        buttons = []
        if role != ROLE_USER:
            buttons.append(InlineKeyboardButton("Пользователь", callback_data="role_user"))
        if role != ROLE_ADMIN:
            buttons.append(InlineKeyboardButton("Администратор", callback_data="role_admin"))
        if role != ROLE_OPERATOR:
            buttons.append(InlineKeyboardButton("Оператор", callback_data="role_operator"))
        buttons.append(InlineKeyboardButton("↩️ Назад", callback_data="back"))
        await query.edit_message_text(
            "Выберите новую роль:",
            reply_markup=InlineKeyboardMarkup([buttons])
        )
        return ADMIN_ROLE_SELECT
    elif data == "block":
        Database.block_user(user_id)
        await query.edit_message_text("Пользователь заблокирован.")
        try:
            await context.bot.send_message(chat_id=user_id, text="Вы заблокированы администратором.")
        except Exception:
            pass
        return ADMIN_USER_ACTION
    elif data == "unblock":
        Database.unblock_user(user_id)
        await query.edit_message_text("Пользователь разблокирован.")
        return ADMIN_USER_ACTION
    elif data == "back":
        await query.edit_message_text("Главное меню администратора.")
        return ADMIN_MAIN

async def admin_role_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = context.user_data['manage_user_id']
    data = query.data
    if data == "role_user":
        Database.set_user_role(user_id, ROLE_USER)
        await query.edit_message_text("Роль пользователя изменена на 'Пользователь'.")
    elif data == "role_admin":
        Database.set_user_role(user_id, ROLE_ADMIN)
        await query.edit_message_text("Роль пользователя изменена на 'Администратор'.")
    elif data == "role_operator":
        Database.set_user_role(user_id, ROLE_OPERATOR)
        await query.edit_message_text("Роль пользователя изменена на 'Оператор'.")
    elif data == "back":
        await query.edit_message_text("Главное меню администратора.")
    # После смены роли показываем главное меню администратора с клавиатурой
    await query.message.reply_text(
        "Главное меню администратора.",
        reply_markup=get_admin_main_menu()
    )
    return ADMIN_MAIN

# Проверка блокировки пользователя для всех пользовательских команд
async def check_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = Database.get_user_info(user.id)
    if user_info.get('blocked'):
        await update.message.reply_text("Вы заблокированы администратором.")
        return True
    return False
