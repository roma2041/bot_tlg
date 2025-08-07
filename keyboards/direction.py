# keyboards/direction.py
# Для клавиатуры выбора направления

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_direction_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏩ В РФ", callback_data='entry'),
            InlineKeyboardButton("⏪ ИЗ РФ", callback_data='exit')
        ],
        [
            InlineKeyboardButton("⏪⏩ В РФ и обратно", callback_data='entry_exit'),
            InlineKeyboardButton("⏪⏩ ИЗ РФ и обратно", callback_data='exit_entry')
        ]
    ])
