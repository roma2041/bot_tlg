from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_checkpoint_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Изварино", callback_data='checkpoint_1'),
            InlineKeyboardButton("Волошино", callback_data='checkpoint_2'),
            InlineKeyboardButton("Гуково", callback_data='checkpoint_3')
        ],
        [
            InlineKeyboardButton("Новошахтинск", callback_data='checkpoint_4'),
            InlineKeyboardButton("Чертково", callback_data='checkpoint_5'),
            InlineKeyboardButton("Успенка", callback_data='checkpoint_6')
        ],
        [
            InlineKeyboardButton("Вознесенка", callback_data='checkpoint_7'),
            InlineKeyboardButton("Куйбышево", callback_data='checkpoint_8'),
            InlineKeyboardButton("Переход К2", callback_data='checkpoint_9')
        ]
    ])

def get_checkpoint_names():
    return [
        "Изварино",
        "Волошино",
        "Гуково",
        "Новошахтинск",
        "Чертково",
        "Успенка",
        "Вознесенка",
        "Куйбышево",
        "Переход К2"
    ]
