# handlers/status.py
# Заглушка для проверки статуса заявки

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes, CallbackQueryHandler
from db import Database
from repositories.request_repo import get_request_status, get_request_full, update_request_status, STATUS_EDITED, STATUS_DUPLICATED, STATUS_CANCELLED
from keyboards.main_menu import get_user_reply_keyboard
from utils.date_utils import format_date_for_display, format_time_for_display
from handlers.admin.admin_users import check_blocked

STATUS_REQUEST_ID = "STATUS_REQUEST_ID"
STATUS_ACTION = "STATUS_ACTION"

def is_free_form_request(request):
    template_fields = [
        'division','direction','checkpoint','date_start','date_end',
        'time_start','time_end','car_brand','people_count','leader_name','cargo'
    ]
    for k in template_fields:
        v = request.get(k)
        if k == 'people_count':
            if v not in [None, '', '-', 0, '0']:
                return False
        else:
            if v not in [None, '', '-']:
                return False
    return bool(request.get('purpose'))

async def ask_request_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    await update.message.reply_text("Введите номер заявки:")
    return STATUS_REQUEST_ID

async def show_request_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    request_id = update.message.text.strip()
    if not request_id.isdigit():
        await update.message.reply_text(
            "Некорректный номер заявки.\nВы вернулись в главное меню.\n")
        reply_markup=get_user_reply_keyboard()
        return ConversationHandler.END
    request_id = int(request_id)
    request = get_request_full(request_id)
    user_id = update.effective_user.id  # Получаем user_id пользователя
    if not request:
        await update.message.reply_text(
            f"Заявка с номером {request_id} не найдена.\n"
            f"Вы вернулись в главное меню.\n",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    # Проверка: пользователь может просматривать только свои заявки
    if str(request.get('user_id')) != str(user_id):
        await update.message.reply_text(
            "Вы можете просматривать только свои заявки.\nВы вернулись в главное меню.",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    context.user_data['status_request_id'] = request_id
    context.user_data['request_data'] = request
    from handlers.edit_request import is_free_form_request, format_free_form_request
    edited = request.get('edited_fields', '')
    if edited is None:
        edited = ''
    if isinstance(edited, str):
        edited = [f.strip() for f in edited.split(',') if f.strip()]
    context.user_data['edited_fields'] = edited
    def highlight(text):
        return f"<b><u>{text}</u></b>"
    date_start = format_date_for_display(request.get('date_start', '-'))
    date_end = format_date_for_display(request.get('date_end', '-'))
    time_start = format_time_for_display(request.get('time_start', '-'))
    time_end = format_time_for_display(request.get('time_end', '-'))
    if is_free_form_request(request):
        text = format_free_form_request(request, request.get('id'))
    else:
        lines = [
            f"📄 Заявка #{request.get('id', '-') }",
            f"🌟 Статус: {request.get('status', '-') }",
            highlight(f"🏢 Подразделение: {request.get('division', '-') }") if 'division' in edited else f"🏢 Подразделение: {request.get('division', '-') }",
            highlight(f"🚧 Направление: {request.get('direction', '-') }") if 'direction' in edited else f"🚧 Направление: {request.get('direction', '-') }",
            highlight(f"🚪 Пункт пропуска: {request.get('checkpoint', '-') }") if 'checkpoint' in edited else f"🚪 Пункт пропуска: {request.get('checkpoint', '-') }",
            highlight(f"📅 Дата: {date_start} - {date_end}") if 'date_start' in edited or 'date_end' in edited else f"📅 Дата: {date_start} - {date_end}",
            highlight(f"⏰ Время: {time_start} - {time_end}") if 'time_start' in edited or 'time_end' in edited else f"⏰ Время: {time_start} - {time_end}",
            highlight(f"🚘 Марки авто: {request.get('car_brand', '-') }") if 'car_brand' in edited else f"🚘 Марки авто: {request.get('car_brand', '-') }",
            highlight(f"👥 Кол-во людей: {request.get('people_count', '-') }") if 'people_count' in edited else f"👥 Кол-во людей: {request.get('people_count', '-') }",
            highlight(f"👨‍✈️ Позывной старшего: {request.get('leader_name', '-') }") if 'leader_name' in edited else f"👨‍✈️ Позывной старшего: {request.get('leader_name', '-') }",
            highlight(f"🔫 Наличие ВВСТ: {request.get('cargo', '-') }") if 'cargo' in edited else f"🔫 Наличие ВВСТ: {request.get('cargo', '-') }",
            highlight(f"💬 Цель перехода: {request.get('purpose', '-') }") if 'purpose' in edited else f"💬 Цель перехода: {request.get('purpose', '-') }"
        ]
        text = '\n'.join(lines)
    keyboard = [
        [InlineKeyboardButton("✅ Выбрать", callback_data="select_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
    ]
    # Если это callback, обновляем сообщение, иначе отправляем новое
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return STATUS_ACTION

def format_free_form_request(request, request_id=None):
    rid = request_id or request.get('id', '-')
    return f"📄 Заявка #{rid}\nСтатус: {request.get('status', '-')}\n{request.get('purpose', '-')}"

async def status_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    request_id = context.user_data.get('status_request_id')
    request = context.user_data.get('request_data') or get_request_full(request_id)
    from handlers.edit_request import is_free_form_request, format_free_form_request
    if query.data == "select_request":
        if request and is_free_form_request(request):
            text = format_free_form_request(request, request.get('id'))
        else:
            edited = request.get('edited_fields', '') if request else ''
            if isinstance(edited, str):
                edited = [f.strip() for f in edited.split(',') if f.strip()]
            def highlight(text):
                return f"<b><u>{text}</u></b>"
            date_start = format_date_for_display(request.get('date_start', '-')) if request else '-'
            date_end = format_date_for_display(request.get('date_end', '-')) if request else '-'
            time_start = format_time_for_display(request.get('time_start', '-')) if request else '-'
            time_end = format_time_for_display(request.get('time_end', '-')) if request else '-'
            lines = [
                f"📄 Заявка #{request.get('id', '-') }",
                f"🌟 Статус: {request.get('status', '-') }",
                highlight(f"🏢 Подразделение: {request.get('division', '-') }") if 'division' in edited else f"🏢 Подразделение: {request.get('division', '-') }",
                highlight(f"🚧 Направление: {request.get('direction', '-') }") if 'direction' in edited else f"🚧 Направление: {request.get('direction', '-') }",
                highlight(f"🚪 Пункт пропуска: {request.get('checkpoint', '-') }") if 'checkpoint' in edited else f"🚪 Пункт пропуска: {request.get('checkpoint', '-') }",
                highlight(f"📅 Дата: {date_start} - {date_end}") if 'date_start' in edited or 'date_end' in edited else f"📅 Дата: {date_start} - {date_end}",
                highlight(f"⏰ Время: {time_start} - {time_end}") if 'time_start' in edited or 'time_end' in edited else f"⏰ Время: {time_start} - {time_end}",
                highlight(f"🚘 Марки авто: {request.get('car_brand', '-') }") if 'car_brand' in edited else f"🚘 Марки авто: {request.get('car_brand', '-') }",
                highlight(f"👥 Кол-во людей: {request.get('people_count', '-') }") if 'people_count' in edited else f"👥 Кол-во людей: {request.get('people_count', '-') }",
                highlight(f"👨‍✈️ Позывной старшего: {request.get('leader_name', '-') }") if 'leader_name' in edited else f"👨‍✈️ Позывной старшего: {request.get('leader_name', '-') }",
                highlight(f"🔫 Наличие ВВСТ: {request.get('cargo', '-') }") if 'cargo' in edited else f"🔫 Наличие ВВСТ: {request.get('cargo', '-') }",
                highlight(f"💬 Цель перехода: {request.get('purpose', '-') }") if 'purpose' in edited else f"💬 Цель перехода: {request.get('purpose', '-') }"
            ]
            text = '\n'.join(lines)
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
            [InlineKeyboardButton("🔄 Продублировать", callback_data="duplicate_request")],
            [InlineKeyboardButton("❌ Отмена заявки", callback_data="cancel_request")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return STATUS_ACTION
    elif query.data == "back_to_menu":
        await query.edit_message_text("Вы вернулись в главное меню.")
        await query.message.reply_text("Главное меню:", reply_markup=get_user_reply_keyboard())
        return ConversationHandler.END
    elif query.data == "edit_request":
        from handlers.new_request import edit_request
        return await edit_request(update, context)
    elif query.data == "duplicate_request":
        update_request_status(request_id, STATUS_DUPLICATED)
        await query.edit_message_text(f"Заявка #{request_id} переведена в статус 'Продублированная'.")
        return ConversationHandler.END
    elif query.data == "cancel_request":
        update_request_status(request_id, STATUS_CANCELLED)
        await query.edit_message_text(f"Заявка #{request_id} отменена.")
        return ConversationHandler.END
    else:
        await query.edit_message_text("Неизвестное действие.")
        return ConversationHandler.END
