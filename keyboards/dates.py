# keyboards/dates.py
# Заглушка для клавиатуры выбора дат

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

WEEKDAYS_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

def get_dates_keyboard(is_start=True):
    today = datetime.now()
    buttons = [
        InlineKeyboardButton(
            f"{WEEKDAYS_RU[date.weekday()]} {date.day}",
            callback_data=f"date_{'start' if is_start else 'end'}_{date.strftime('%d.%m')}"
        )
        for date in [today + timedelta(days=i) for i in range(3)]
    ]
    return InlineKeyboardMarkup([buttons])
