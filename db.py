# db.py
import logging
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, ROLE_USER, ROLE_ADMIN, ROLE_OPERATOR

logger = logging.getLogger('db')

class Database:
    @staticmethod
    def get_connection():
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except Error as e:
            logger.error(f"Ошибка подключения к MySQL: {e}")
            return None

    @staticmethod
    def check_connection():
        conn = Database.get_connection()
        if conn:
            conn.close()
            return True
        return False

    @staticmethod
    def create_tables():
        try:
            conn = Database.get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        full_name VARCHAR(255),
                        role VARCHAR(32) NOT NULL DEFAULT 'user'
                    )
                ''')
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        division VARCHAR(255),
                        direction VARCHAR(50),
                        checkpoint VARCHAR(100),
                        date_start VARCHAR(50),
                        date_end VARCHAR(50),
                        time_start VARCHAR(5),
                        time_end VARCHAR(5),
                        car_brand VARCHAR(255),
                        people_count INT,
                        leader_name VARCHAR(255),
                        cargo TEXT,
                        purpose TEXT,
                        status VARCHAR(32) NOT NULL DEFAULT 'Новая',
                        edited_fields TEXT,
                        operator_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def get_user_role(user_id):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return 'user'
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                return row['role'] if row else 'user'
        except Error as e:
            logger.error(f"Ошибка при получении роли пользователя: {e}")
            return 'user'
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def set_user(user_id, username, full_name, role='user'):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO users (user_id, username, full_name, role)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE username=VALUES(username), full_name=VALUES(full_name), role=VALUES(role)
                ''', (user_id, username, full_name, role))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Ошибка при добавлении/обновлении пользователя: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def get_user_info(user_id):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return {'id': user_id, 'username': '', 'role': ROLE_USER, 'blocked': False}
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT user_id, username, role, blocked FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['user_id'],
                        'username': row['username'],
                        'role': row['role'],
                        'blocked': bool(row['blocked'])
                    }
                return {'id': user_id, 'username': '', 'role': ROLE_USER, 'blocked': False}
        except Error as e:
            logger.error(f"Ошибка при получении информации о пользователе: {e}")
            return {'id': user_id, 'username': '', 'role': ROLE_USER, 'blocked': False}
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def block_user(user_id):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute('UPDATE users SET blocked = 1 WHERE user_id = %s', (user_id,))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Ошибка при блокировке пользователя: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def unblock_user(user_id):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute('UPDATE users SET blocked = 0 WHERE user_id = %s', (user_id,))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Ошибка при разблокировке пользователя: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def set_user_role(user_id, role):
        conn = None
        try:
            conn = Database.get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute('UPDATE users SET role = %s WHERE user_id = %s', (role, user_id))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Ошибка при изменении роли пользователя: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    @staticmethod
    def get_operators():
        """
        Получить список всех операторов (user_id, username, full_name).
        Логирует количество найденных операторов.
        """
        conn = None
        try:
            # Принудительно создаем новое соединение
            conn = mysql.connector.connect(**DB_CONFIG)
            if not conn:
                logger.info("[get_operators] Нет соединения с БД.")
                return []
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT user_id, username, full_name FROM users WHERE role = %s ORDER BY user_id", (ROLE_OPERATOR,))
                operators = cursor.fetchall()
                logger.info(f"[get_operators] Найдено операторов: {len(operators)}")
                for op in operators:
                    logger.info(f"[get_operators] Оператор: {op['user_id']} - "
                               f"{op['full_name']} (@{op['username']})")
                return operators
        except Error as e:
            logger.error(f"Ошибка при получении списка операторов: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                conn.close()
