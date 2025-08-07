# handlers/edit_request.py
# Модуль обработчиков этапов редактирования существующей заявки через ConversationHandler.
# Реализует пошаговый диалог для редактирования информации о заявке, загруженной из БД.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from handlers.status import STATUS_ACTION
from keyboards.direction import get_direction_keyboard
from keyboards.checkpoint import get_checkpoint_keyboard, get_checkpoint_names
from keyboards.people_count import get_people_count_keyboard
from keyboards.dates import get_dates_keyboard
from time_picker import TimePicker
from repositories.request_repo import get_request_full, update_request_fields, update_request_status, STATUS_EDITED, STATUS_DUPLICATED, STATUS_CANCELLED
from config import DIVISION, DIRECTION, CHECKPOINT, DATE_START, DATE_END, TIME_START, TIME_END, CAR_BRAND, PEOPLE_COUNT, LEADER_NAME, CARGO, PURPOSE, ADMIN_CHAT_ID
from keyboards.main_menu import get_user_reply_keyboard
from handlers.new_request import get_edit_fields_keyboard
from handlers.admin.admin_requests import notify_admins_about_duplicate
from utils.date_utils import format_date_for_display, format_time_for_display
from utils.request_time import is_allowed_request_time, get_time_limits_str

EDIT_FIELD = "EDIT_FIELD"
SELECT_ACTIONS = "SELECT_ACTIONS"
CONFIRM_EDIT = "CONFIRM_EDIT"
AWAIT_FREE_FORM_EDIT = "AWAIT_FREE_FORM_EDIT"  # Добавлена константа состояния для свободной формы редактирования

__all__ = [
    'division_edit',
    'direction_edit',
    'checkpoint_edit',
    'date_start_edit',
    'date_end_edit',
    'time_start_edit',
    'time_end_edit',
    'car_brand_edit',
    'people_count_edit',
    'leader_name_edit',
    'cargo_edit',
    'purpose_edit',
    'cancel_request',
    'duplicate_request',
    'back_to_menu',
    'back_to_actions',
    'select_request',
]

# --- Вспомогательные функции ---
def highlight(text):
    return f"<b><u>{text}</u></b>"

def is_free_form_request(request):
    template_fields = [
        'division', 'direction', 'checkpoint', 'date_start', 'date_end',
        'time_start', 'time_end', 'car_brand', 'people_count',
        'leader_name', 'cargo'
    ]
    return all(not request.get(f) for f in template_fields) and request.get('purpose')

def format_free_form_request(request, request_id=None):
    rid = request_id or request.get('id', '')
    # Если заявка в статусе 'На уточнении', показываем только поле purpose
    if request.get('status') == 'На уточнении':
        return f"📄 Заявка #{rid} (свободная форма, на уточнении):\n{request.get('purpose', '')}"
    return f"📄 Заявка #{rid} (свободная форма):\n{request.get('purpose', '')}"

def format_request_text(data, edited_fields=None):
    # Если заявка свободной формы и статус 'На уточнении', показываем только purpose
    if is_free_form_request(data) and data.get('status') == 'На уточнении':
        rid = data.get('id', '')
        return f"📄 Заявка #{rid} (свободная форма, на уточнении):\n{data.get('purpose', '')}"
    edited_fields = edited_fields or []
    def f(field, label, icon):
        val = data.get(field, '')
        if not val:
            return None
        # Форматирование дат и времени
        if field == 'date_start' or field == 'date_end':
            val = format_date_for_display(val)
        if field == 'time_start' or field == 'time_end':
            val = format_time_for_display(val)
        line = f"{icon} {label}: {val}"
        return highlight(line) if field in edited_fields else line
    lines = [
        f("id", "Номер заявки", "📄"),
        f("status", "Статус", "🌟"),
        f("division", "Подразделение", "🏢"),
        f("direction", "Направление", "🚧"),
        f("checkpoint", "Пункт пропуска", "🚪"),
        f("date_start", "Дата начала", "📅"),
        f("date_end", "Дата окончания", "📅"),
        f("time_start", "Время начала", "⏰"),
        f("time_end", "Время окончания", "⏰"),
        f("car_brand", "Марки авто", "🚘"),
        f("people_count", "Кол-во людей", "👥"),
        f("leader_name", "Позывной старшего", "👨‍✈️"),
        f("cargo", "Наличие ВВСТ", "🔫"),
        f("purpose", "Цель перехода", "💬"),
    ]
    # Исключаем пустые строки
    return '\n'.join([line for line in lines if line])

# --- 1. Показываем заявку с кнопками "Выбрать" и "Назад" ---
async def show_request_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_id = update.message.text.strip()
    if not request_id.isdigit():
        await update.message.reply_text("Некорректный номер заявки. Введите число.")
        return STATUS_ACTION
    request_id = int(request_id)
    request = get_request_full(request_id)
    if not request:
        await update.message.reply_text(
            f"Заявка с номером {request_id} не найдена.",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    context.user_data['status_request_id'] = request_id
    context.user_data['request_data'] = request
    context.user_data['edited_fields'] = []
    # Если свободная форма и статус На уточнении, показываем только purpose
    if is_free_form_request(request) and request.get('status') == 'На уточнении':
        text = format_free_form_request(request, request_id)
    elif is_free_form_request(request):
        text = format_free_form_request(request, request_id)
    else:
        text = format_request_text(request)
    keyboard = [
        [InlineKeyboardButton("✔️ Выбрать", callback_data="select_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return STATUS_ACTION

# --- 2. Меню из 4 действий ---
async def select_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    # Проверка времени работы бота
    if not is_allowed_request_time():
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            f"Операции с заявками доступны только {get_time_limits_str()}.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    request = context.user_data.get('request_data')
    # Если свободная форма и статус На уточнении, показываем только purpose
    if is_free_form_request(request) and request.get('status') == 'На уточнение':
        text = format_free_form_request(request, request.get('id'))
    elif is_free_form_request(request):
        text = format_free_form_request(request, request.get('id'))
    else:
        text = format_request_text(request, context.user_data.get('edited_fields', []))
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("🔄 Продублировать", callback_data="duplicate_request")],
        [InlineKeyboardButton("❌ Отмена заявки", callback_data="cancel_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return STATUS_ACTION

# --- 3. Меню выбора поля для редактирования ---
async def edit_request_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    request = context.user_data.get('request_data')
    # Для свободной формы заявки сразу предлагаем ввести новый текст заявки
    if request and is_free_form_request(request):
        await query.edit_message_text("Введите новый текст заявки:")
        return AWAIT_FREE_FORM_EDIT
    # Для обычных заявок используем стандартную клавиатуру
    await query.edit_message_text(
        "Выберите поле для редактирования:",
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_FIELD

# Новый этап: обработка ввода нового текста для свободной формы заявки
async def after_free_form_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        new_text = update.message.text
        context.user_data['request_data']['purpose'] = new_text
        # Сохраняем в БД
        request_id = context.user_data.get('status_request_id')
        if request_id:
            data_to_save = context.user_data['request_data'].copy()
            update_request_fields(request_id, data_to_save)
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")]
        ]
        text = format_free_form_request(context.user_data['request_data'], request_id)
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_EDIT

# --- 4. Обработка выбора поля ---
async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field_map = {
        "edit_division": ("division", "Введите новое значение для поля: Подразделение"),
        "edit_direction": ("direction", "Выберите новое направление:"),
        "edit_checkpoint": ("checkpoint", "Выберите новый пункт пропуска:"),
        "edit_date_start": ("date_start", "Выберите новую дату начала:"),
        "edit_date_end": ("date_end", "Выберите новую дату окончания:"),
        "edit_time_start": ("time_start", "Выберите новое время начала:"),
        "edit_time_end": ("time_end", "Выберите новое время окончания:"),
        "edit_car_brand": ("car_brand", "Введите новые марки авто:"),
        "edit_people_count": ("people_count", "Выберите новое количество людей:"),
        "edit_leader_name": ("leader_name", "Введите нового старшего:"),
        "edit_cargo": ("cargo", "Введите новое ВВСТ:"),
        "edit_purpose": ("purpose", "Введите новую цель перехода:"),
    }
    field, prompt = field_map.get(query.data, (None, None))
    context.user_data["edit_field"] = field
    # Для выбора через клавиатуру
    if query.data == "edit_direction":
        await query.edit_message_text(prompt, reply_markup=get_direction_keyboard())
        return DIRECTION
    elif query.data == "edit_checkpoint":
        await query.edit_message_text(prompt, reply_markup=get_checkpoint_keyboard())
        return CHECKPOINT
    elif query.data == "edit_date_start":
        await query.edit_message_text(prompt, reply_markup=get_dates_keyboard(is_start=True))
        return DATE_START
    elif query.data == "edit_date_end":
        await query.edit_message_text(prompt, reply_markup=get_dates_keyboard(is_start=False))
        return DATE_END
    elif query.data == "edit_time_start":
        await query.edit_message_text(prompt, reply_markup=TimePicker.generate(time_type="start"))
        return TIME_START
    elif query.data == "edit_time_end":
        await query.edit_message_text(prompt, reply_markup=TimePicker.generate(time_type="end"))
        return TIME_END
    elif query.data == "edit_people_count":
        await query.edit_message_text(prompt, reply_markup=get_people_count_keyboard())
        return PEOPLE_COUNT
    elif field:
        await query.edit_message_text(prompt)
        state_map = {
            "division": DIVISION,
            "direction": DIRECTION,
            "checkpoint": CHECKPOINT,
            "date_start": DATE_START,
            "date_end": DATE_END,
            "time_start": TIME_START,
            "time_end": TIME_END,
            "car_brand": CAR_BRAND,
            "people_count": PEOPLE_COUNT,
            "leader_name": LEADER_NAME,
            "cargo": CARGO,
            "purpose": PURPOSE,
        }
        return state_map.get(field, ConversationHandler.END)
    else:
        await query.edit_message_text("Ошибка выбора поля.")
        return ConversationHandler.END

# --- 5. Обработка ввода нового значения поля ---
async def after_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    field = context.user_data.get("edit_field")
    if field and update.message:
        context.user_data['request_data'][field] = update.message.text
        # --- сохраняем историю редактированных полей ---
        sync_edited_fields(context)
        # Добавляем текущее поле, если его нет
        if field not in context.user_data["edited_fields"]:
            context.user_data["edited_fields"].append(field)
        context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
        # Sохраняем изменения в БД, включая edited_fields как строку
        data_to_save = context.user_data['request_data'].copy()
        data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
    # Проверка времени для редактирования
    if not is_allowed_request_time():
        await update.message.reply_text(
            f"Редактирование заявок возможно только {get_time_limits_str()}.")
        return ConversationHandler.END
    if isinstance(field, str):
        update_request_fields(context.user_data['status_request_id'], data_to_save)
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")]
#        [InlineKeyboardButton("Назад", callback_data="back_to_actions")] # бираем кнопку Назад, чтобы не было путаницы
    ]
    text = format_request_text(context.user_data['request_data'], context.user_data['edited_fields'])
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    # Определяем, в каком контексте мы находимся
    # Если есть status_request_id, значит редактируем существующую заявку
    if context.user_data.get('status_request_id'):
        return CONFIRM_EDIT
    else:
        # Если нет status_request_id, значит создаем новую заявку
        return "AWAIT_CONFIRM"

# --- 6. ✅ Подтвердить изменения ---
async def confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    request_id = context.user_data['status_request_id']
    update_request_status(request_id, STATUS_EDITED)
    request = get_request_full(request_id)
    admin_message = format_request_text(request, context.user_data.get('edited_fields', []))
    # Удалено обычное сообщение админу, оставлен только вызов notify_admins_about_edited
    from handlers.admin.admin_requests import notify_admins_about_edited
    admin_ids = [ADMIN_CHAT_ID]
    await notify_admins_about_edited(context, request_id, admin_ids)
    await query.edit_message_text(f"Заявка #{request_id} успешно отредактирована.\n Статус: {STATUS_EDITED}\n" + admin_message, parse_mode="HTML")
    await query.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_user_reply_keyboard())
    return ConversationHandler.END

# --- 7. 🔄 Продублировать заявку ---
async def duplicate_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    query = update.callback_query
    await query.answer()
    if not is_allowed_request_time():
        await query.edit_message_text(
            f"Дублирование заявок возможно только {get_time_limits_str()}.")
        return ConversationHandler.END
    request_id = context.user_data['status_request_id']
    request = get_request_full(request_id)
    if not request:
        await query.edit_message_text("Ошибка: заявка не найдена.")
        return ConversationHandler.END
    user_id = query.from_user.id
    update_request_status(request_id, STATUS_DUPLICATED)
    # Получаем список администраторов (замените на реальный список, если их несколько)
    admin_ids = [ADMIN_CHAT_ID]
    await notify_admins_about_duplicate(context, request_id, admin_ids)
    # После отправки админам не закрываем окно, а показываем сообщение пользователю
    await query.edit_message_text(f"Заявка #{request_id} успешно продублирована и отправлена на рассмотрение администратору.", parse_mode="HTML")
    return ConversationHandler.END

# --- 8. ❌ Отмена заявки ---
async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    query = update.callback_query
    await query.answer()
    if not is_allowed_request_time():
        await query.edit_message_text(
            f"Отмена заявок возможна только {get_time_limits_str()}.")
        return ConversationHandler.END
    request_id = context.user_data['status_request_id']
    update_request_status(request_id, STATUS_CANCELLED)
    request = get_request_full(request_id)
    if not request:
        await query.edit_message_text("Ошибка: заявка не найдена.")
        return ConversationHandler.END
    
    # Уведомляем администратора
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"\U0001F4DD Отмененная заявка #{request_id} (Статус: {STATUS_CANCELLED}):\n" + format_request_text(request),
        parse_mode="HTML"
    )
    
    # Уведомляем оператора, если заявка была назначена оператору
    operator_id = request.get('operator_id')
    if operator_id:
        try:
            await context.bot.send_message(
                chat_id=operator_id,
                text=f"❌ Заявка #{request_id} была отменена пользователем.\n\n" + format_request_text(request),
                parse_mode="HTML"
            )
        except Exception as e:
            # Если не удалось отправить сообщение оператору, логируем ошибку
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Не удалось уведомить оператора {operator_id} об отмене заявки {request_id}: {e}")
    
    await query.edit_message_text(f"📄 Заявка #{request_id} отменена. Вы вернулись в главное меню.")
    return ConversationHandler.END

# --- 9. Назад в главное меню ---
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Вы вернулись в главное меню.")
    return ConversationHandler.END

# --- 10. Назад в меню действий ---
async def back_to_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = format_request_text(context.user_data['request_data'], context.user_data.get('edited_fields', []))
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("🔄 Продублировать", callback_data="duplicate_request")],
        [InlineKeyboardButton("❌ Отмена заявки", callback_data="cancel_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return SELECT_ACTIONS

# --- Служебная функция для синхронизации edited_fields с БД ---
def sync_edited_fields(context):
    if "edited_fields" not in context.user_data:
        context.user_data["edited_fields"] = []
    request_id = context.user_data.get('status_request_id')
    if request_id:
        request = get_request_full(request_id)
        db_edited = request.get('edited_fields', '') if request else ''
        if db_edited is None:
            db_edited = ''
        if isinstance(db_edited, str):
            db_edited = [f.strip() for f in db_edited.split('.') if f.strip()]
        for f in db_edited:
            if f not in context.user_data["edited_fields"]:
                context.user_data["edited_fields"].append(f)

# --- Обработчики этапов редактирования для импорта ---
async def division_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        sync_edited_fields(context)
        await query.edit_message_text("Введите новое значение для поля: Подразделение")
        context.user_data["edit_field"] = "division"
        return DIVISION
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)

async def direction_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id')
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    direction_map = {
        'entry': 'В РФ',
        'exit': 'ИЗ РФ',
        'entry_exit': 'В РФ и обратно',
        'exit_entry': 'ИЗ РФ и обратно'
    }
    data = query.data
    if data in direction_map:
        context.user_data['request_data']['direction'] = direction_map[data]
        field = 'direction'
        if field not in context.user_data["edited_fields"]:
            context.user_data["edited_fields"].append(field)
        context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
        request_id = context.user_data.get('status_request_id')
        if request_id:
            data_to_save = context.user_data['request_data'].copy()
            data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
            update_request_fields(request_id, data_to_save)
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
        ]
        text = format_request_text(context.user_data['request_data'], context.user_data["edited_fields"])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return CONFIRM_EDIT
    else:
        await query.edit_message_text("Ошибка выбора направления.")
        return ConversationHandler.END

async def checkpoint_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id')
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    checkpoint_names = get_checkpoint_names()
    try:
        checkpoint_num = int(query.data.split('_')[1])
        checkpoint_name = checkpoint_names[checkpoint_num - 1]
    except Exception:
        await query.edit_message_text("Ошибка выбора пункта пропуска.")
        return ConversationHandler.END
    context.user_data['request_data']['checkpoint'] = checkpoint_name
    field = 'checkpoint'
    if field not in context.user_data["edited_fields"]:
        context.user_data["edited_fields"].append(field)
    context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
    request_id = context.user_data.get('status_request_id')
    if request_id:
        data_to_save = context.user_data['request_data'].copy()
        data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
        update_request_fields(request_id, data_to_save)
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
    ]
    text = format_request_text(context.user_data['request_data'], context.user_data["edited_fields"])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_EDIT

async def date_start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id')
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    try:
        date_str = query.data.split('_')[2]
    except Exception:
        await query.edit_message_text("Ошибка выбора даты.")
        return ConversationHandler.END
    context.user_data['request_data']['date_start'] = date_str
    field = 'date_start'
    if field not in context.user_data["edited_fields"]:
        context.user_data["edited_fields"].append(field)
    context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
    request_id = context.user_data.get('status_request_id')
    if request_id:
        data_to_save = context.user_data['request_data'].copy()
        data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
        update_request_fields(request_id, data_to_save)
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
    ]
    text = format_request_text(context.user_data['request_data'], context.user_data.get('edited_fields'))
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_EDIT

async def date_end_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id')
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    try:
        date_str = query.data.split('_')[2]
    except Exception:
        await query.edit_message_text("Ошибка выбора даты.")
        return ConversationHandler.END
    context.user_data['request_data']['date_end'] = date_str
    field = 'date_end'
    if field not in context.user_data["edited_fields"]:
        context.user_data["edited_fields"].append(field)
    context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
    request_id = context.user_data.get('status_request_id')
    if request_id:
        data_to_save = context.user_data['request_data'].copy()
        data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
        update_request_fields(request_id, data_to_save)
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
    ]
    text = format_request_text(context.user_data['request_data'], context.user_data.get("edited_fields", []))
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_EDIT

async def time_start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id'
        )
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    data = query.data.split('_')
    if len(data) < 3:
        await query.edit_message_text("Ошибка выбора времени.")
        return ConversationHandler.END
    if data[2] == 'hour':
        context.user_data['time_start_hour'] = int(data[3])
        context.user_data['time_start_minute'] = None
    elif data[2] == 'min':
        if context.user_data.get('time_start_hour') is not None:
            context.user_data['time_start_minute'] = int(data[3])
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    elif data[2] == 'reset':
        context.user_data['time_start_hour'] = None
        context.user_data['time_start_minute'] = None
    elif data[2] == 'confirm':
        if context.user_data.get('time_start_hour') is not None:
            minute = context.user_data.get('time_start_minute')
            if minute is None:
                minute = 0
            hour = context.user_data.get('time_start_hour')
            if hour is None:
                await query.edit_message_text("Ошибка: не выбран час.")
                return ConversationHandler.END
            time_str = f"{hour:02d}:{minute:02d}"
            context.user_data['request_data']['time_start'] = time_str
            field = 'time_start'
            if field not in context.user_data["edited_fields"]:
                context.user_data["edited_fields"].append(field)
            context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
            request_id = context.user_data.get('status_request_id')
            if request_id:
                data_to_save = context.user_data['request_data'].copy()
                data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
                update_request_fields(request_id, data_to_save)
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
            ]
            text = format_request_text(context.user_data['request_data'], context.user_data['edited_fields'])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return CONFIRM_EDIT
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    from time_picker import TimePicker
    await query.edit_message_text(
        text="Выберите время начала проезда:",
        reply_markup=TimePicker.generate(
            hour=context.user_data.get('time_start_hour'),
            minute=context.user_data.get('time_start_minute'),
            time_type="start"
        )
    )
    return TIME_START

async def time_end_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'request_data' not in context.user_data or not context.user_data['request_data']:
        request_id = context.user_data.get('status_request_id'
        )
        if request_id:
            request = get_request_full(request_id)
            if request:
                context.user_data['request_data'] = request
            else:
                context.user_data['request_data'] = {}
        else:
            context.user_data['request_data'] = {}
    sync_edited_fields(context)
    data = query.data.split('_')
    if len(data) < 3:
        await query.edit_message_text("Ошибка выбора времени.")
        return ConversationHandler.END
    if data[2] == 'hour':
        context.user_data['time_end_hour'] = int(data[3])
        context.user_data['time_end_minute'] = None
    elif data[2] == 'min':
        if context.user_data.get('time_end_hour') is not None:
            context.user_data['time_end_minute'] = int(data[3])
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    elif data[2] == 'reset':
        context.user_data['time_end_hour'] = None
        context.user_data['time_end_minute'] = None
    elif data[2] == 'confirm':
        if context.user_data.get('time_end_hour') is not None:
            minute = context.user_data.get('time_end_minute')
            if minute is None:
                minute = 0
            hour = context.user_data.get('time_end_hour')
            if hour is None:
                await query.edit_message_text("Ошибка: не выбран час.")
                return ConversationHandler.END
            time_str = f"{hour:02d}:{minute:02d}"
            context.user_data['request_data']['time_end'] = time_str
            field = 'time_end'
            if field not in context.user_data["edited_fields"]:
                context.user_data["edited_fields"].append(field)
            context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
            request_id = context.user_data.get('status_request_id')
            if request_id:
                data_to_save = context.user_data['request_data'].copy()
                data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
                update_request_fields(request_id, data_to_save)
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
            ]
            text = format_request_text(context.user_data['request_data'], context.user_data.get("edited_fields", []))
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return CONFIRM_EDIT
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    from time_picker import TimePicker
    await query.edit_message_text(
        text="Выберите время окончания проезда:",
        reply_markup=TimePicker.generate(
            hour=context.user_data.get('time_end_hour'),
            minute=context.user_data.get('time_end_minute'),
            time_type="end"
        )
    )
    return TIME_END

async def people_count_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if 'request_data' not in context.user_data or not context.user_data['request_data']:
            request_id = context.user_data.get('status_request_id')
            if request_id:
                request = get_request_full(request_id)
                if request:
                    context.user_data['request_data'] = request
                else:
                    context.user_data['request_data'] = {}
            else:
                context.user_data['request_data'] = {}
        sync_edited_fields(context)
        if query.data == 'people_manual':
            await query.edit_message_text("Введите количество людей вручную:")
            return PEOPLE_COUNT
        else:
            try:
                count = int(query.data.split('_')[1])
            except Exception:
                await query.edit_message_text("Ошибка выбора количества людей.")
                return ConversationHandler.END
            context.user_data['request_data']['people_count'] = count
            field = 'people_count'
            if field not in context.user_data["edited_fields"]:
                context.user_data["edited_fields"].append(field)
            context.user_data["edited_fields"] = list(dict.fromkeys(context.user_data["edited_fields"]))
            request_id = context.user_data.get('status_request_id'
            )
            if request_id:
                data_to_save = context.user_data['request_data'].copy()
                data_to_save['edited_fields'] = ','.join(context.user_data['edited_fields'])
                update_request_fields(request_id, data_to_save)
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_edit")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back_to_actions")]
            ]
            text = format_request_text(context.user_data['request_data'], context.user_data.get("edited_fields", []))
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return CONFIRM_EDIT
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)

async def car_brand_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        sync_edited_fields(context)
        await query.edit_message_text("Введите новые марки авто:")
        context.user_data["edit_field"] = "car_brand"
        return CAR_BRAND
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)

async def leader_name_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        sync_edited_fields(context)
        await query.edit_message_text("Введите нового старшего:")
        context.user_data["edit_field"] = "leader_name"
        return LEADER_NAME
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)

async def cargo_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        sync_edited_fields(context)
        await query.edit_message_text("Введите новое ВВСТ:")
        context.user_data["edit_field"] = "cargo"
        return CARGO
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)

async def purpose_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        sync_edited_fields(context)
        await query.edit_message_text("Введите новую цель перехода:")
        context.user_data["edit_field"] = "purpose"
        return PURPOSE
    elif update.message:
        # Если пришло текстовое сообщение, обработку делает after_edit
        return await after_edit(update, context)