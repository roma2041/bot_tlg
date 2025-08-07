# config.py
# Конфигурационный файл проекта.
# Содержит настройки для подключения к БД, токен бота, роли и этапы диалога.

import os
from dotenv import load_dotenv

load_dotenv()

# Параметры подключения к базе данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'user1'),
    'password': os.getenv('DB_PASSWORD', '123456789'),
    'database': os.getenv('DB_NAME', 'checkpoint_bot2')
}

# Токен Telegram-бота и ID чата администратора
TOKEN = os.getenv('TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# ID чатов операторов
OPERATOR_1_CHAT_ID = os.getenv('OPERATOR_1_CHAT_ID')
OPERATOR_2_CHAT_ID = os.getenv('OPERATOR_2_CHAT_ID')

# Роли пользователей
ROLE_ADMIN = 'admin'
ROLE_OPERATOR = 'operator'
ROLE_USER = 'user'
ROLES = [ROLE_ADMIN, ROLE_OPERATOR, ROLE_USER]

# Этапы диалога ConversationHandler
MENU = 100
DIVISION, DIRECTION, CHECKPOINT, CUSTOM_CHECKPOINT, DATE_START, DATE_END, TIME_START, TIME_END, CAR_BRAND, PEOPLE_COUNT, LEADER_NAME, CARGO, PURPOSE = range(13)
