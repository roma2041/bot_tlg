from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_checkpoint_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Пункт № 1", callback_data='checkpoint_1'),
            InlineKeyboardButton("Пункт № 2", callback_data='checkpoint_2'),
            InlineKeyboardButton("Пункт № 3", callback_data='checkpoint_3')
        ],
        [
            InlineKeyboardButton("Пункт № 4", callback_data='checkpoint_4'),
            InlineKeyboardButton("Пункт № 5", callback_data='checkpoint_5'),
            InlineKeyboardButton("Пункт № 6", callback_data='checkpoint_6')
        ],
        [
            InlineKeyboardButton("Пункт № 7", callback_data='checkpoint_7'),
            InlineKeyboardButton("Пункт № 8", callback_data='checkpoint_8'),
            InlineKeyboardButton("Пункт № 9", callback_data='checkpoint_9')
        ]
    ])

def get_checkpoint_names():
    return [
        "Пункт № 1",
        "Пункт № 2",
        "Пункт № 3",
        "Пункт № 4",
        "Пункт № 5",
        "Пункт № 6",
        "Пункт № 7",
        "Пункт № 8",
        "Пункт № 9"
    ]

