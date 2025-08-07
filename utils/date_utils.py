# utils/date_utils.py
# Функции для работы с датами

from datetime import datetime, timedelta

def format_date_for_display(date_str):
    """
    Преобразует дату из формата 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS',
    или объект datetime.date/datetime.datetime в 'DD.MM.YY'.
    Если строка не соответствует формату, возвращает исходное значение.
    """
    if not date_str:
        return ""
    # Если это объект datetime.date или datetime.datetime, преобразуем в строку
    if hasattr(date_str, 'strftime'):
        date_str = date_str.strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return date_str
    return dt.strftime("%d.%m.%y")

def format_time_for_display(time_str):
    """
    Преобразует время из формата 'HH:MM:SS', 'HH:MM', datetime.time, datetime.datetime, datetime.timedelta в 'HH:MM'.
    Если строка не соответствует формату, возвращает исходное значение.
    """
    if not time_str:
        return ""
    # Если это объект datetime.time или datetime.datetime, преобразуем в строку
    if hasattr(time_str, 'strftime'):
        time_str = time_str.strftime("%H:%M:%S")
    # Если это timedelta, преобразуем в строку HH:MM:SS
    elif isinstance(time_str, timedelta):
        total_seconds = int(time_str.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    try:
        dt = datetime.strptime(time_str, "%H:%M:%S")
    except ValueError:
        try:
            dt = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return time_str
    return dt.strftime("%H:%M")