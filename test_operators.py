#!/usr/bin/env python3
"""
Тестовый скрипт для проверки получения операторов из БД.
Помогает диагностировать проблему с кнопкой "Подтвердить".
"""

import mysql.connector
from config import DB_CONFIG, ROLE_OPERATOR
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_get_operators():
    """Тестирует получение операторов из БД"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn:
            logger.error("Нет соединения с БД")
            return []
        
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT user_id, username, full_name, role FROM users WHERE role = %s ORDER BY user_id", 
                (ROLE_OPERATOR,)
            )
            operators = cursor.fetchall()
            logger.info(f"Найдено операторов: {len(operators)}")
            for op in operators:
                logger.info(f"Оператор: {op['user_id']} - {op['full_name']} (@{op['username']}) - {op['role']}")
            return operators
    except Exception as e:
        logger.error(f"Ошибка при получении операторов: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

def test_get_all_users():
    """Тестирует получение всех пользователей"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn:
            logger.error("Нет соединения с БД")
            return []
        
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT user_id, username, full_name, role FROM users ORDER BY user_id")
            users = cursor.fetchall()
            logger.info(f"Всего пользователей: {len(users)}")
            for user in users:
                logger.info(f"Пользователь: {user['user_id']} - {user['full_name']} (@{user['username']}) - {user['role']}")
            return users
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    print("=== Тест получения операторов ===")
    operators = test_get_operators()
    
    print("\n=== Тест получения всех пользователей ===")
    users = test_get_all_users()
    
    print("\n=== Анализ ===")
    operator_users = [u for u in users if u['role'] == ROLE_OPERATOR]
    print(f"Операторов через фильтрацию: {len(operator_users)}")
    print(f"Операторов через прямой запрос: {len(operators)}")
    
    if len(operators) != len(operator_users):
        print("⚠️ ВНИМАНИЕ: Разное количество операторов!")
    else:
        print("✅ Количество операторов совпадает") 