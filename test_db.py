#!/usr/bin/env python3
"""
Простой тест для проверки работы с БД
"""

import mysql.connector
from config import DB_CONFIG, ROLE_OPERATOR
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_db_connection():
    """Тестирует подключение к БД и получение операторов"""
    try:
        logger.info("Тестируем подключение к БД...")
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("Подключение к БД успешно")
        
        with conn.cursor(dictionary=True) as cursor:
            # Проверяем таблицу users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            users_count = cursor.fetchone()['count']
            logger.info(f"Всего пользователей в БД: {users_count}")
            
            # Получаем операторов
            cursor.execute(
                "SELECT user_id, username, full_name, role FROM users WHERE role = %s ORDER BY user_id", 
                (ROLE_OPERATOR,)
            )
            operators = cursor.fetchall()
            logger.info(f"Найдено операторов: {len(operators)}")
            
            for op in operators:
                logger.info(f"Оператор: {op['user_id']} - {op['full_name']} (@{op['username']}) - {op['role']}")
            
            # Проверяем таблицу requests
            cursor.execute("SELECT COUNT(*) as count FROM requests")
            requests_count = cursor.fetchone()['count']
            logger.info(f"Всего заявок в БД: {requests_count}")
            
            # Получаем последние заявки
            cursor.execute("SELECT id, user_id, status FROM requests ORDER BY id DESC LIMIT 5")
            recent_requests = cursor.fetchall()
            logger.info("Последние заявки:")
            for req in recent_requests:
                logger.info(f"Заявка #{req['id']} - пользователь {req['user_id']} - статус {req['status']}")
        
        conn.close()
        logger.info("Тест завершен успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании БД: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=== Тест подключения к БД ===")
    success = test_db_connection()
    if success:
        print("✅ Тест прошел успешно")
    else:
        print("❌ Тест не прошел") 