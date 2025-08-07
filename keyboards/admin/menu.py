# keyboards/admin/menu.py
# Клавиатура для главного меню администратора.

from telegram import ReplyKeyboardMarkup

def get_admin_main_menu():
    return ReplyKeyboardMarkup([
        ["Администрирование"],
        ["🔍 Просмотр заявок"],
        ["Выгрузка заявок в Excel"]
    ], resize_keyboard=True)

# Здесь будут дополнительные клавиатуры для подменю администратора

# Клавиатура для подменю "Администрирование"
def get_admin_manage_menu():
    return ReplyKeyboardMarkup([
        ["Пригласить (заглушка)"],
        ["Управление пользователями"],
        ["↩️ Назад"]
    ], resize_keyboard=True)

# Клавиатура для подменю "Просмотр заявок"
def get_admin_requests_menu():
    return ReplyKeyboardMarkup([
        ["🔍 Просмотр заявок"],
        ["🔍 Проверка статуса заявки"],
        ["↩️ Назад"]
    ], resize_keyboard=True)

# Клавиатура для подменю "Выгрузка заявок в Excel"
def get_admin_export_menu():
    return ReplyKeyboardMarkup([
        ["За все время"],
        ["За период"],
        ["↩️ Назад"]
    ], resize_keyboard=True)
