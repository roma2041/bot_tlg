# handlers/start.py
# Модуль обработчиков команд /start и /cancel, а также меню создания заявки.
# Отвечает за регистрацию пользователя, определение роли и вывод главного меню.

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from db import Database
from keyboards.main_menu import get_user_reply_keyboard, get_user_main_menu
from keyboards.admin.menu import get_admin_main_menu
from keyboards.operator.menu import get_operator_reply_keyboard
from config import ROLE_USER, ROLE_ADMIN, ROLE_OPERATOR, MENU
from handlers.admin.admin_users import check_blocked
from utils.request_time import is_allowed_request_time, get_time_limits_str

# Обработчик команды /start: регистрирует пользователя и показывает главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END

    user = update.effective_user
    # Получаем текущую роль из БД
    current_role = Database.get_user_role(user.id)
    if current_role == 'user':
        # Если пользователь новый, добавляем с ролью user
        Database.set_user(user.id, user.username, user.full_name or user.mention_html(), role=ROLE_USER)
    else:
        # Если пользователь уже есть, не меняем роль!
        Database.set_user(user.id, user.username, user.full_name or user.mention_html(), role=current_role)
    role = Database.get_user_role(user.id)
    context.user_data['role'] = role

    # Открываем меню в зависимости от роли
    if role == ROLE_ADMIN:
        await update.message.reply_text(
            f"Добро пожаловать, ваша роль: {role}",
            reply_markup=get_admin_main_menu()
        )
    elif role == ROLE_OPERATOR:
        await update.message.reply_text(
            f"Добро пожаловать, ваша роль: {role}",
            reply_markup=get_operator_reply_keyboard()
        )
    else:
        await update.message.reply_text(
            f"Добро пожаловать, ваша роль: {role}",
            reply_markup=get_user_reply_keyboard()
        )

# Обработчик отмены заявки
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = context.user_data.get('role', ROLE_USER)
    if role == ROLE_ADMIN:
        await update.message.reply_text(
            'Регистрация заявки отменена.',
            reply_markup=get_admin_main_menu()
        )
    elif role == ROLE_OPERATOR:
        await update.message.reply_text(
            'Регистрация заявки отменена.',
            reply_markup=get_operator_reply_keyboard()
        )
    else:
        await update.message.reply_text(
            'Регистрация заявки отменена.',
            reply_markup=get_user_reply_keyboard()
        )

# Меню выбора способа создания заявки
async def user_menu_create_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    if not is_allowed_request_time():
        await update.message.reply_text(
            f"Создание заявок возможно только {get_time_limits_str()}.")
        return ConversationHandler.END
    await update.message.reply_text(
        'Выберите способ создания заявки:',
        reply_markup=get_user_main_menu()
    )
    return MENU
