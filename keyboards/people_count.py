# keyboards/people_count.py
# Заглушка для клавиатуры выбора количества людей

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_people_count_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(i), callback_data=f'people_{i}') for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f'people_{i}') for i in range(6, 11)],
        [InlineKeyboardButton("Ручной ввод", callback_data='people_manual')]
    ])
