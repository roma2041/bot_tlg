from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from repositories.request_repo import get_request_full, update_request_status, STATUS_COMPLETED, STATUS_CANCELLED, get_requests_for_operator_by_date_range
from config import ADMIN_CHAT_ID
from datetime import datetime, timedelta
from keyboards.operator.menu import get_operator_reply_keyboard, get_operator_view_inline_keyboard
from utils.date_utils import format_date_for_display, format_time_for_display

OPERATOR_REQUEST_ACTION = 400
OPERATOR_REQUEST_REASON = 401
OPERATOR_VIEW_MENU = 410
OPERATOR_VIEW_LEADER = 411
OPERATOR_VIEW_ID = 412

def format_operator_request_text(request):
    template_fields = [
        'division', 'direction', 'checkpoint', 'date_start', 'date_end',
        'time_start', 'time_end', 'car_brand', 'people_count',
        'leader_name', 'cargo'
    ]
    is_free_form = all(not request.get(f) for f in template_fields) and request.get('purpose')
    if is_free_form:
        return f"Заявка #{request['id']} (Статус: {request.get('status', '')})\n{request.get('purpose', '')}"
    edited_fields = request.get('edited_fields', [])
    if isinstance(edited_fields, str):
        edited_fields = [f.strip() for f in edited_fields.split(',') if f.strip()]
    def highlight(text):
        return f"<b><u>{text}</u></b>"
    def line(field, label, value):
        return highlight(f"{label}: {value}") if field in edited_fields else f"{label}: {value}"
    date_start = format_date_for_display(request.get('date_start', ''))
    date_end = format_date_for_display(request.get('date_end', ''))
    time_start = format_time_for_display(request.get('time_start', ''))
    time_end = format_time_for_display(request.get('time_end', ''))
    lines = [
        f"Заявка #{request['id']} (Статус: {request.get('status', '')})",
        line('division', 'Подразделение', request.get('division', '')),
        line('direction', 'Направление', request.get('direction', '')),
        line('checkpoint', 'Пункт пропуска', request.get('checkpoint', '')),
        line('date_start', 'Дата', f"{date_start} - {date_end}"),
        line('time_start', 'Время', f"{time_start} - {time_end}"),
        line('car_brand', 'Марки авто', request.get('car_brand', '')),
        line('people_count', 'Кол-во людей', request.get('people_count', '')),
        line('leader_name', 'Позывной старшего', request.get('leader_name', '')),
        line('cargo', 'Наличие ВВСТ', request.get('cargo', '')),
        line('purpose', 'Цель перехода', request.get('purpose', '')),
#        f"ID пользователя: {request.get('user_id', '')}"
    ]
    return "\n".join(lines)

async def send_request_to_operator(context, operator_id, request_id):
    request = get_request_full(request_id)
    text = format_operator_request_text(request)
    # Если заявка в статусе Продублировать, показываем специальную кнопку и обязательно показываем все поля заявки
    if request.get('status') == 'Продублировать':
        keyboard = [
            [InlineKeyboardButton("🔄 Продублировать", callback_data=f"operator_duplicate_{request_id}")] 
        ]
        await context.bot.send_message(chat_id=operator_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"operator_confirm_{request_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"operator_cancel_{request_id}")]
        ]
        await context.bot.send_message(chat_id=operator_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

def log_and_return_false(msg):
    return False

async def operator_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("operator_confirm_"):
        request_id = int(data.split('_')[2])
        result = update_request_status(request_id, STATUS_COMPLETED)
        request = get_request_full(request_id)
        if not request:
            await query.edit_message_text(f"Ошибка: заявка не найдена.")
            return ConversationHandler.END
        try:
            text = format_operator_request_text(request)
            await query.edit_message_text(f"Заявка #{request_id} исполнена.\n\n{text}", parse_mode="HTML")
            await context.bot.send_message(chat_id=request['user_id'], text=f"Ваша заявка #{request_id} исполнена оператором.")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Заявка #{request_id} исполнена оператором.")
        except Exception:
            pass
        return ConversationHandler.END
    elif data.startswith("operator_duplicate_"):
        request_id = int(data.split('_')[2])
        result = update_request_status(request_id, STATUS_COMPLETED)
        request = get_request_full(request_id)
        if not request:
            await query.edit_message_text(f"Ошибка: заявка не найдена.")
            return ConversationHandler.END
        try:
            text = format_operator_request_text(request)
            await query.edit_message_text(f"Заявка #{request_id} продублирована и исполнена.\n\n{text}", parse_mode="HTML")
            await context.bot.send_message(chat_id=request['user_id'], text=f"Ваша заявка #{request_id} продублирована и исполнена оператором.")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Заявка #{request_id} продублирована и исполнена оператором.")
        except Exception:
            pass
        return ConversationHandler.END
    elif data.startswith("operator_cancel_"):
        request_id = int(data.split('_')[2])
        context.user_data['operator_cancel_request_id'] = request_id
        await query.edit_message_text("Введите причину отмены заявки:")
        return OPERATOR_REQUEST_REASON

async def operator_request_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import logging
    logging.warning("operator_request_reason called")
    if not hasattr(update, 'message') or not hasattr(update.message, 'from_user'):
        await update.message.reply_text("Ошибка: не удалось определить пользователя.")
        return ConversationHandler.END

    request_id = context.user_data.get('operator_cancel_request_id')
    if not request_id:
        await update.message.reply_text("Ошибка: не удалось определить заявку для отмены.")
        return ConversationHandler.END

    reason = update.message.text
    request = get_request_full(request_id)
    if not request:
        await update.message.reply_text("Ошибка: заявка не найдена.")
        return ConversationHandler.END

    result = update_request_status(request_id, STATUS_CANCELLED)
    if not result:
        await update.message.reply_text("Ошибка: не удалось обновить статус заявки.")
        return ConversationHandler.END

    try:
        await context.bot.send_message(chat_id=request['user_id'], text=f"Ваша заявка #{request_id} отменена оператором. Причина: {reason}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Заявка #{request_id} отменена оператором. Причина: {reason}")
        await update.message.reply_text("Причина отмены отправлена.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке уведомлений: {e}")

    return ConversationHandler.END

async def operator_view_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите способ фильтрации заявок:",
        reply_markup=get_operator_view_inline_keyboard()
    )
    return OPERATOR_VIEW_MENU

async def operator_view_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "view_by_leader":
        await query.edit_message_text("Введите ФИО старшего для поиска заявок:")
        return OPERATOR_VIEW_LEADER
    elif data == "view_by_id":
        await query.edit_message_text("Введите номер заявки:")
        return OPERATOR_VIEW_ID
    elif data == "view_all_period":
        operator_id = query.from_user.id
        today = datetime.now().date()
        date_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        requests = get_requests_for_operator_by_date_range(operator_id, date_from, date_to)
        if not requests:
            await query.edit_message_text("Заявок за последние 2 дня и на 2 дня вперед не найдено.", reply_markup=get_operator_reply_keyboard())
            return ConversationHandler.END
        for req in requests:
            text = format_operator_request_text(req)
            await query.message.reply_text(text, parse_mode="HTML")
        await query.message.reply_text("Вы вернулись в меню оператора.", reply_markup=get_operator_reply_keyboard())
        return ConversationHandler.END

async def operator_view_leader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    operator_id = update.effective_user.id
    leader = update.message.text.strip().lower()
    today = datetime.now().date()
    date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    requests = get_requests_for_operator_by_date_range(operator_id, date_from, date_to)
    filtered = [r for r in requests if leader in (r.get('leader_name') or '').lower()]
    if not filtered:
        await update.message.reply_text("Заявки по данному старшему не найдены.", reply_markup=get_operator_reply_keyboard())
        return ConversationHandler.END
    for req in filtered:
        text = format_operator_request_text(req)
        await update.message.reply_text(text, parse_mode="HTML")
    await update.message.reply_text("Вы вернулись в меню оператора.", reply_markup=get_operator_reply_keyboard())
    return ConversationHandler.END

async def operator_view_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    operator_id = update.effective_user.id
    req_id = update.message.text.strip()
    if not req_id.isdigit():
        await update.message.reply_text("Введите корректный номер заявки.", reply_markup=get_operator_reply_keyboard())
        return ConversationHandler.END
    today = datetime.now().date()
    date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    requests = get_requests_for_operator_by_date_range(operator_id, date_from, date_to)
    filtered = [r for r in requests if str(r['id']) == req_id]
    if not filtered:
        await update.message.reply_text("Заявка с таким номером не найдена.", reply_markup=get_operator_reply_keyboard())
        return ConversationHandler.END
    for req in filtered:
        text = format_operator_request_text(req)
        await update.message.reply_text(text, parse_mode="HTML")
    await update.message.reply_text("Вы вернулись в меню оператора.", reply_markup=get_operator_reply_keyboard())
    return ConversationHandler.END
