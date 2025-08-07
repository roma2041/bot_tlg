# repositories/request_repo.py
# Модуль для работы с заявлениями (CRUD).
# Сохраняет заявку в базу данных и возвращает её ID.
# Добавлена поддержка статусов заявки.

import logging
from db import Database
from datetime import datetime

logger = logging.getLogger(__name__)

# Статусы заявки
STATUS_NEW = 'Новая'
STATUS_ON_REVIEW = 'На проверке'
STATUS_ON_CLARIFICATION = 'На уточнении'
STATUS_COMPLETED = 'Исполненная'
STATUS_CANCELLED = 'Отмененная'
STATUS_EDITED = 'Отредактированная'
STATUS_DUPLICATED = 'Продублировать'
STATUS_IN_PROGRESS = 'В работе'
ALL_STATUSES = [STATUS_NEW, STATUS_ON_REVIEW, STATUS_ON_CLARIFICATION, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_EDITED, STATUS_DUPLICATED, STATUS_IN_PROGRESS]

# Сохраняет заявку с указанным статусом

def save_request(user_data, user_id, status=STATUS_NEW):
    """
    Сохраняет заявку в БД. Возвращает ID новой заявки.
    user_data: dict с данными заявки
    user_id: Telegram ID пользователя
    status: статус заявки
    """
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return None
        with conn.cursor() as cursor:
            # Преобразуем даты к формату YYYY-MM-DD
            date_start = user_data.get('date_start')
            date_end = user_data.get('date_end')
            def parse_date(date_str):
                try:
                    # Поддержка форматов 'дд.мм' и 'YYYY-MM-DD'
                    if not date_str:
                        return None
                    if len(date_str) == 5 and '.' in date_str:
                        return datetime.strptime(date_str, "%d.%m").replace(year=datetime.now().year).strftime("%Y-%m-%d")
                    elif len(date_str) == 10 and '-' in date_str:
                        # Уже в формате YYYY-MM-DD
                        return date_str
                    else:
                        return date_str if date_str else None
                except Exception:
                    return date_str if date_str else None
            date_start_fmt = parse_date(date_start) if date_start else None
            date_end_fmt = parse_date(date_end) if date_end else None
            # edited_fields всегда пустой при создании новой заявки
            edited_fields = ''
            query = """
                INSERT INTO requests (
                    user_id, division, direction, checkpoint,
                    date_start, date_end, time_start, time_end,
                    car_brand, people_count, leader_name, cargo, purpose, status, edited_fields
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                user_id,
                user_data.get('division'), user_data.get('direction'), user_data.get('checkpoint'),
                date_start_fmt, date_end_fmt, user_data.get('time_start'), user_data.get('time_end'),
                user_data.get('car_brand'), user_data.get('people_count'), user_data.get('leader_name'),
                user_data.get('cargo'), user_data.get('purpose'), status, edited_fields
            )
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при сохранении заявки: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

# Функция для смены статуса заявки

def update_request_status(request_id, new_status, reason=None):
    """
    Обновляет статус заявки по её ID. Если указана причина отмены, сохраняет её.
    """
    if new_status not in ALL_STATUSES:
        raise ValueError(f"Недопустимый статус: {new_status}")
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return False
        with conn.cursor() as cursor:
            if reason is not None:
                cursor.execute("UPDATE requests SET status = %s, reason = %s WHERE id = %s", (new_status, reason, request_id))
            else:
                cursor.execute("UPDATE requests SET status = %s WHERE id = %s", (new_status, request_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заявки: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

# Функция для получения статуса заявки

def get_request_status(request_id):
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return None
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT status FROM requests WHERE id = %s", (request_id,))
            row = cursor.fetchone()
            return row['status'] if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении статуса заявки: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_request_full(request_id):
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return None
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT r.*, u.full_name
                FROM requests r
                LEFT JOIN users u ON r.user_id = u.user_id
                WHERE r.id = %s
            """, (request_id,))
            row = cursor.fetchone()
            return row
    except Exception as e:
        logger.error(f"Ошибка при получении заявки: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

def update_request_fields(request_id, user_data):
    """
    Обновляет все поля заявки по её ID.
    user_data: dict с новыми данными заявки
    """
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return False
        with conn.cursor() as cursor:
            # Преобразуем даты к формату YYYY-MM-DD
            date_start = user_data.get('date_start')
            date_end = user_data.get('date_end')
            def parse_date(date_str):
                try:
                    # Поддержка форматов 'дд.мм' и 'YYYY-MM-DD'
                    if not date_str:
                        return None
                    if len(date_str) == 5 and '.' in date_str:
                        return datetime.strptime(date_str, "%d.%m").replace(year=datetime.now().year).strftime("%Y-%m-%d")
                    elif len(date_str) == 10 and '-' in date_str:
                        # Уже в формате YYYY-MM-DD
                        return date_str
                    else:
                        return date_str if date_str else None
                except Exception:
                    return date_str if date_str else None
            date_start_fmt = parse_date(date_start) if date_start else None
            date_end_fmt = parse_date(date_end) if date_end else None
            edited_fields = ''.join(user_data.get('edited_fields', [])) if user_data.get('edited_fields') else None
            query = """
                UPDATE requests SET
                    division = %s,
                    direction = %s,
                    checkpoint = %s,
                    date_start = %s,
                    date_end = %s,
                    time_start = %s,
                    time_end = %s,
                    car_brand = %s,
                    people_count = %s,
                    leader_name = %s,
                    cargo = %s,
                    purpose = %s,
                    edited_fields = %s
                WHERE id = %s
            """
            values = (
                user_data.get('division'), user_data.get('direction'), user_data.get('checkpoint'),
                date_start_fmt, date_end_fmt, user_data.get('time_start'), user_data.get('time_end'),
                user_data.get('car_brand'), user_data.get('people_count'), user_data.get('leader_name'), user_data.get('cargo'), user_data.get('purpose'), edited_fields, request_id
            )
            cursor.execute(query, values)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении заявки: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_all_users():
    """
    Получить список всех пользователей.
    Возвращает список словарей с user_id, username, full_name, role.
    """
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            logger.error("[get_all_users] Нет соединения с БД")
            return []
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT user_id, username, full_name, role FROM users ORDER BY user_id")
            users = cursor.fetchall()
            logger.info(f"[get_all_users] Получено пользователей: {len(users)}")
            for user in users:
                logger.info(f"[get_all_users] Пользователь: {user['user_id']} - "
                           f"{user['full_name']} (@{user['username']}) - {user['role']}")
            return users
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

def assign_operator(request_id, operator_id):
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return False
        with conn.cursor() as cursor:
            cursor.execute("UPDATE requests SET operator_id = %s WHERE id = %s", (operator_id, request_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f'Ошибка при назначении оператора: {e}')
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_requests_for_operator_by_date_range(operator_id, date_from, date_to):
    """
    Получить ВСЕ заявки с датой date_start в диапазоне [date_from, date_to],
    включая заявки, исполненные другими операторами.
    Также возвращает все заявки в свободной форме 
    (где date_start is NULL и есть purpose).
    """
    conn = None
    try:
        conn = Database.get_connection()
        if not conn:
            return []
        with conn.cursor(dictionary=True) as cursor:
            query = """
                SELECT * FROM requests
                WHERE (
                        (date_start >= %s AND date_start <= %s)
                        OR (date_start IS NULL AND purpose IS NOT NULL)
                    )
                ORDER BY id ASC
            """
            cursor.execute(query, (date_from, date_to))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении заявок для оператора: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()
