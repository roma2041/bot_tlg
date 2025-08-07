from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def get_operator_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Просмотр заявок"]
    ], resize_keyboard=True)

def get_operator_view_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 По старшему", callback_data="view_by_leader")],
        [InlineKeyboardButton("📄 По номеру заявки", callback_data="view_by_id")],
        [InlineKeyboardButton("Показать заявки за сутки", callback_data="view_all_period")]
    ])
