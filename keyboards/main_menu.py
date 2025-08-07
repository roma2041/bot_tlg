# keyboards/main_menu.py
# Модуль генерации клавиатур для главного меню и меню создания заявки.
# Формирует ReplyKeyboardMarkup в зависимости от роли пользователя.

from telegram import ReplyKeyboardMarkup
from config import ROLE_USER

# Главное меню для разных ролей
# Админ: администрирование и управление заявками
# Оператор: просмотр заявок
# Пользователь: создание и управление своими заявками
def get_user_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🆕 Создать заявку", "🔍 Проверить статус"],
        ["↩️ Назад", "/start"]
    ], resize_keyboard=True)

# Меню выбора способа создания заявки для пользователя
def get_user_main_menu():
    return ReplyKeyboardMarkup([
        ["🧾 По образцу", "🗒 В свободной форме"],
        ["↩️ Назад", "/start"]
    ], resize_keyboard=True)

# --- Обработчик возврата в главное меню и сброса данных пользователя ---
async def handle_back(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "Вы вернулись в главное меню.",
        reply_markup=get_user_reply_keyboard()
    )
    from telegram.ext import ConversationHandler
    return ConversationHandler.END
