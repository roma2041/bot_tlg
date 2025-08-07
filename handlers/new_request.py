# handlers/new_request.py
# Модуль обработчиков этапов создания новой заявки через ConversationHandler.
# Реализует пошаговый диалог для сбора информации о заявке и её сохранения.
# Добавлен обработчик для свободной формы заявки.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from keyboards.direction import get_direction_keyboard
from keyboards.checkpoint import get_checkpoint_keyboard, get_checkpoint_names
from keyboards.people_count import get_people_count_keyboard
from keyboards.dates import get_dates_keyboard
from time_picker import TimePicker
from repositories.request_repo import save_request, STATUS_NEW, get_request_full
from config import DIVISION, DIRECTION, CHECKPOINT, DATE_START, DATE_END, TIME_START, TIME_END, CAR_BRAND, PEOPLE_COUNT, LEADER_NAME, CARGO, PURPOSE, ADMIN_CHAT_ID, MENU
from keyboards.main_menu import get_user_reply_keyboard
from config import ROLE_USER
from handlers.admin.admin_users import check_blocked
from handlers.admin.admin_requests import admin_requests_entry, get_admin_request_text_and_keyboard
from utils.request_time import is_allowed_request_time, get_time_limits_str

EDIT_FIELD = "EDIT_FIELD"

# Кнопки для выбора поля
def get_edit_fields_keyboard():
    fields = [
        ("🏢 Подразделение", "edit_division"),
        ("🚧 Направление", "edit_direction"),
        ("📅 Дата начала", "edit_date_start"),
        ("📅 Дата окончания", "edit_date_end"),
        ("⏰ Время начала", "edit_time_start"),
        ("⏰ Время окончания", "edit_time_end"),
        ("🚪 Пункт пропуска", "edit_checkpoint"),
        ("🚘 Марки авто", "edit_car_brand"),
        ("👥 Кол-во людей", "edit_people_count"),
        ("👨‍✈️ Позывной старшего", "edit_leader_name"),
        ("🔫 Наличие ВВСТ", "edit_cargo"),
        ("💬 Цель перехода", "edit_purpose"),
    ]
    keyboard = []
    for i in range(0, len(fields), 2):
        row = [InlineKeyboardButton(fields[i][0], callback_data=fields[i][1])]
        if i + 1 < len(fields):
            row.append(InlineKeyboardButton(fields[i + 1][0], callback_data=fields[i + 1][1]))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data['edited_fields'] = []
    await update.message.reply_text("Для начала введите ваше подразделение:")
    return DIVISION

async def division_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data['division'] = update.message.text
    # Если редактируем поле
    if context.user_data.get("edit_field") == "division":
        return await after_edit(update, context)
    await update.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        "🚧 Выберите направление:",
        reply_markup=get_direction_keyboard()
    )
    return DIRECTION

async def direction_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction_map = {
        'entry': 'В РФ',
        'exit': 'ИЗ РФ',
        'entry_exit': 'В РФ и обратно',
        'exit_entry': 'ИЗ РФ и обратно'
    }
    context.user_data['direction'] = direction_map[query.data]
    await query.edit_message_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}",
    )
    await query.message.reply_text("🚪 Выберите пункт пропуска:", reply_markup=get_checkpoint_keyboard())
    return CHECKPOINT

async def checkpoint_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    checkpoint_names = get_checkpoint_names()
    checkpoint_num = int(query.data.split('_')[1])
    checkpoint_name = checkpoint_names[checkpoint_num - 1]
    context.user_data['checkpoint'] = checkpoint_name
    await query.edit_message_text(f"Пункт пропуска: {checkpoint_name}")
    await query.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        "📅 Выберите дата начала проезда:",
        reply_markup=get_dates_keyboard(is_start=True)
    )
    return DATE_START

async def date_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    date_str = query.data.split('_')[2]
    context.user_data['date_start'] = date_str
    await query.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата с: {context.user_data['date_start']} по {context.user_data.get('date_end', '__.__')}\n"
        "📅 Выберите дату окончания проезда:",
        reply_markup=get_dates_keyboard(is_start=False)
    )
    return DATE_END

async def date_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    date_str = query.data.split('_')[2]
    context.user_data['date_end'] = date_str
    await query.message.reply_text(
        "Выберите время начала проезда:",
        reply_markup=TimePicker.generate(time_type="start")
    )
    return TIME_START

async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    time_type = data[1]
    prefix = f"time_{time_type}"
    if f"{prefix}_hour" not in context.user_data:
        context.user_data[f"{prefix}_hour"] = None
        context.user_data[f"{prefix}_minute"] = None
    if data[2] == 'hour':
        context.user_data[f"{prefix}_hour"] = int(data[3])
        context.user_data[f"{prefix}_minute"] = None
    elif data[2] == 'min':
        if context.user_data[f"{prefix}_hour"] is not None:
            context.user_data[f"{prefix}_minute"] = int(data[3])
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    elif data[2] == 'reset':
        context.user_data[f"{prefix}_hour"] = None
        context.user_data[f"{prefix}_minute"] = None
    elif data[2] == 'confirm':
        if context.user_data[f"{prefix}_hour"] is not None:
            minute = context.user_data[f"{prefix}_minute"] if context.user_data[f"{prefix}_minute"] is not None else 10
            time_str = f"{context.user_data[f'{prefix}_hour']:02d}:{minute:02d}"
            context.user_data[f"time_{time_type}"] = time_str
            await query.edit_message_text(f"Время {'начала' if time_type == 'start' else 'окончания'}: {time_str}")
            if time_type == "start":
                await query.message.reply_text(
                    "Выберите время окончания проезда:",
                    reply_markup=TimePicker.generate(time_type="end")
                )
                return TIME_END
            else:
                await query.message.reply_text(
                    f"🏢 Подразделение: {context.user_data['division']}\n"
                    f"🚧 Направление: {context.user_data['direction']}\n"
                    f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
                    f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
                    f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
                    "🚘 Введите марку ТС и кол-во:\n(КамАЗ - 1, УАЗ - 2, Тайота Камри - 1)"
                )
                return CAR_BRAND
        else:
            await query.answer("Сначала выберите час", show_alert=True)
            return
    await query.edit_message_text(
        text=f"Выберите время {'начала' if time_type == 'start' else 'окончания'} проезда:",
        reply_markup=TimePicker.generate(
            hour=context.user_data[f"{prefix}_hour"],
            minute=context.user_data[f"{prefix}_minute"],
            time_type=time_type
        )
    )
    return TIME_START if time_type == "start" else TIME_END

async def car_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data['car_brand'] = update.message.text
    if context.user_data.get("edit_field") == "car_brand":
        return await after_edit(update, context)
    await update.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
        f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
        f"🚘 Марки авто: {context.user_data['car_brand']}\n"
        "👥 Выберите количество людей:",
        reply_markup=get_people_count_keyboard()
    )
    return PEOPLE_COUNT

async def people_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'people_manual':
        await query.edit_message_text("Введите количество людей вручную:")
        return PEOPLE_COUNT
    else:
        count = int(query.data.split('_')[1])
        context.user_data['people_count'] = count
        await query.edit_message_text(
            f"🏢 Подразделение: {context.user_data['division']}\n"
            f"🚧 Направление: {context.user_data['direction']}\n"
            f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
            f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
            f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
            f"🚘 Марки авто: {context.user_data['car_brand']}\n"
            f"👥 Кол-во людей: {context.user_data['people_count']}\n"
            "👨‍✈️ Введите позывной старшего:",
        )
        return LEADER_NAME

async def manual_people_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    try:
        count = int(update.message.text)
        if count <= 0:
            raise ValueError
        context.user_data['people_count'] = count
        if context.user_data.get("edit_field") == "people_count":
            return await after_edit(update, context)
        await update.message.reply_text(
            f"🏢 Подразделение: {context.user_data['division']}\n"
            f"🚧 Направление: {context.user_data['direction']}\n"
            f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
            f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
            f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
            f"🚘 Марки авто: {context.user_data['car_brand']}\n"
            f"👥 Кол-во людей: {context.user_data['people_count']}\n"
            "👨‍✈️ Введите позывной старшего:",
        )
        return LEADER_NAME
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число (больше 0):")
        return PEOPLE_COUNT

async def leader_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data['leader_name'] = update.message.text
    if context.user_data.get("edit_field") == "leader_name":
        return await after_edit(update, context)
    await update.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
        f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
        f"🚘 Марки авто: {context.user_data['car_brand']}\n"
        f"👥 Кол-во людей: {context.user_data['people_count']}\n"
        f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}\n"
        "🔫 Введите назв. и кол-во ВВСТ:\n(Без оружия.\nПМ - 2ед, патроны 9мм - 32шт.)\n"
    )
    return CARGO

async def cargo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data['cargo'] = update.message.text
    if context.user_data.get("edit_field") == "cargo":
        return await after_edit(update, context)
    await update.message.reply_text(
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата перехода с: {context.user_data['date_start']} по {context.user_data['date_end']}\n"
        f"⏰ Время с: {context.user_data['time_start']} по {context.user_data['time_end']}\n"
        f"🚘 Марки авто: {context.user_data['car_brand']}\n"
        f"👥 Кол-во людей: {context.user_data['people_count']}\n"
        f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}\n"
        f"🔫 Наличие ВВСТ: {context.user_data['cargo']}\n"
        f"💬 Цель перехода:"
    )
    return PURPOSE

async def purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    context.user_data['purpose'] = update.message.text
    if context.user_data.get("edit_field") == "purpose":
        return await after_edit(update, context)
    required_fields = [
        'division', 'direction', 'checkpoint', 'date_start', 'date_end',
        'time_start', 'time_end', 'car_brand', 'people_count',
        'leader_name', 'cargo', 'purpose'
    ]
    if any(field not in context.user_data for field in required_fields):
        await update.message.reply_text("? Отсутствуют обязательные поля")
        return ConversationHandler.END
    text = (
        f"\U0001F4DD Ваша заявка:\n"
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата: {context.user_data['date_start']} - {context.user_data['date_end']}\n"
        f"⏰ Время: {context.user_data['time_start']} - {context.user_data['time_end']}\n"
        f"🚘 Марки авто: {context.user_data['car_brand']}\n"
        f"👥 Кол-во людей: {context.user_data['people_count']}\n"
        f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}\n"
        f"🔫 Наличие ВВСТ: {context.user_data['cargo']}\n"
        f"💬 Цель перехода: {context.user_data['purpose']}\n"
        f"\nПроверьте данные и подтвердите отправку заявки."
    )
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_request")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_request")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return "AWAIT_CONFIRM"

async def edit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Выберите поле для редактирования:",
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_FIELD

async def edit_field(update, context):
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
        "edit_purpose": ("purpose", "Введите новую цель:"),
    }
    field, prompt = field_map.get(query.data, (None, None))
    context.user_data["edit_field"] = field
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

async def after_edit(update, context):
    field = context.user_data.get("edit_field")
    if field and update.message:
        context.user_data[field] = update.message.text
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_request")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_request")]
    ]
    text = (
        f"📄 Ваша заявка:\n"
        f"🏢 Подразделение: {context.user_data['division']}\n"
        f"🚧 Направление: {context.user_data['direction']}\n"
        f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
        f"📅 Дата: {context.user_data['date_start']} - {context.user_data['date_end']}\n"
        f"⏰ Время: {context.user_data['time_start']} - {context.user_data['time_end']}\n"
        f"🚘 Марки авто: {context.user_data['car_brand']}\n"
        f"👥 Кол-во людей: {context.user_data['people_count']}\n"
        f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}\n"
        f"🔫 Наличие ВВСТ: {context.user_data['cargo']}\n"
        f"💬 Цель перехода: {context.user_data['purpose']}\n"
        f"⚠️ Проверьте данные и подтвердите отправку заявки."
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return "AWAIT_CONFIRM"

async def confirm_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    query = update.callback_query
    await query.answer()
    if not is_allowed_request_time():
        await query.edit_message_text(
            f"Приём заявок возможен только {get_time_limits_str()}.")
        return ConversationHandler.END
    request_id = save_request(context.user_data, query.from_user.id, status=STATUS_NEW)
    if not request_id:
        await query.edit_message_text("Ошибка при сохранении заявки. Попробуйте позже.")
        return ConversationHandler.END
    request = get_request_full(request_id)
    context.user_data['request_data'] = request
    # Формируем текст и клавиатуру через функцию
    text, keyboard = await get_admin_request_text_and_keyboard(request)
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=text,
        reply_markup=keyboard
    )
    # Отправка пользователю подтверждения
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text = f"📄 Ваша заявка #{request_id} отправлена на рассмотрение.\n"
               f"📄 Статус: {STATUS_NEW}\n"
               f"🏢 Подразделение: {context.user_data['division']}\n"
               f"🚧 Направление: {context.user_data['direction']}\n"
               f"🚪 Пункт пропуска: {context.user_data['checkpoint']}\n"
               f"📅 Дата: {context.user_data['date_start']} - {context.user_data['date_end']}\n"
               f"⏰ Время: {context.user_data['time_start']} - {context.user_data['time_end']}\n"
               f"🚘 Марки авто: {context.user_data['car_brand']}\n"
               f"👥 Кол-во людей: {context.user_data['people_count']}\n"
               f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}\n"
               f"🔫 Наличие ВВСТ: {context.user_data['cargo']}\n"
               f"💬 Цель перехода: {context.user_data['purpose']}\n",
        reply_markup=get_user_reply_keyboard()
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    return ConversationHandler.END

async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    query = update.callback_query
    await query.answer()
    if not is_allowed_request_time():
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"Отмена заявок возможна только {get_time_limits_str()}.",
            reply_markup=get_user_reply_keyboard()
        )
        await query.edit_message_reply_markup(reply_markup=None)
        return ConversationHandler.END
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="📄 Заявка отменена. Вы вернулись в главное меню.",
        reply_markup=get_user_reply_keyboard()
    )
    await query.edit_message_reply_markup(reply_markup=None)
    return ConversationHandler.END

# Обработчик редактирования заявки (заглушка, можно доработать для выбора поля)
async def edit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Если редактируем существующую заявку, подгружаем данные
    request_id = context.user_data.get('status_request_id')
    if request_id:
        request = get_request_full(request_id)
        if request:
            # Заполняем user_data для редактирования
            for k in ['division','direction','checkpoint','date_start','date_end','time_start','time_end','car_brand','people_count','leader_name','cargo','purpose']:
                context.user_data[k] = request.get(k)
            # Загружаем edited_fields из базы для этой заявки
            context.user_data['edited_fields'] = request.get('edited_fields', '').split(',') if request.get('edited_fields') else []
            await query.edit_message_text(
                "Выберите поле для редактирования:",
                reply_markup=get_edit_fields_keyboard()
            )
            return EDIT_FIELD
    # Если нет request_id, обычное поведение
    await query.edit_message_text(
        "Выберите поле для редактирования:",
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_FIELD

# Обработчик выбора поля для редактирования
async def edit_field(update, context):
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
        "edit_purpose": ("purpose", "Введите новую цель:"),
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
    # Для текстовых полей
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

# После изменения любого поля возвращаем три кнопки подтверждения
async def after_edit(update, context):
    field = context.user_data.get("edit_field")
    # Сохраняем новое значение только если это текстовое поле
    if field and update.message:
        context.user_data[field] = update.message.text
    # Сохраняем историю редактированных полей
    if "edited_fields" not in context.user_data:
        context.user_data["edited_fields"] = []
    # Добавляем поле, если его нет в списке
    if field and field not in context.user_data["edited_fields"]:
        context.user_data["edited_fields"].append(field)
    # --- Сохраняем изменения сразу в БД, если редактируется существующая заявка ---
    request_id = context.user_data.get('status_request_id')
    if request_id:
        from repositories.request_repo import update_request_fields
        update_request_fields(request_id, context.user_data)
    # --- конец блока сохранения ---
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_request")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_request")]
    ]
    def highlight_date(text):
        return f"<b><u><i>{text}</i></u></b>"
    def highlight_time(text):
        return f"<b><u><i>{text}</i></u></b>"
    def highlight(text):
        return f"<b><u>{text}</u></b>"
    from datetime import datetime
    def format_date(date_str):
        if not date_str:
            return ""
        # YYYY-MM-DD -> дд.мм
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%d.%m")
        except Exception:
            return date_str
    def format_time(time_str):
        return time_str if time_str else ""
    edited = context.user_data["edited_fields"]
    lines = [
        "Данные обновлены. Проверьте заявку и подтвердите отправку.",
#        "\U0001F4DD Ваша заявка:",
        highlight(f"🏢 Подразделение: {context.user_data['division']}" ) if 'division' in edited else f"🏢 Подразделение: {context.user_data['division']}",
        highlight(f"🚧 Направление: {context.user_data['direction']}" ) if 'direction' in edited else f"🚧 Направление: {context.user_data['direction']}",
        highlight(f"🚪 Пункт пропуска: {context.user_data['checkpoint']}" ) if 'checkpoint' in edited else f"🚪 Пункт пропуска: {context.user_data['checkpoint']}",
       # highlight(f"📅 Дата: {context.user_data['date_start']} - {context.user_data['date_end']}" ) if 'date_start' in edited or 'date_end' in edited else f"📅 Дата: {context.user_data['date_start']} - {context.user_data['date_end']}",
      #  highlight(f"⏰ Время: {context.user_data['time_start']} - {context.user_data['time_end']}" ) if 'time_start' in edited or 'time_end' in edited else f"⏰ Время: {context.user_data['time_start']} - {context.user_data['time_end']}",
        highlight_date(f"📅 Дата: {format_date(context.user_data['date_start'])} - {format_date(context.user_data['date_end'])}" ) if 'date_start' in edited or 'date_end' in edited else f"📅 Дата: {format_date(context.user_data['date_start'])} - {format_date(context.user_data['date_end'])}",
        highlight_time(f"⏰ Время: {format_time(context.user_data['time_start'])} - {format_time(context.user_data['time_end'])}" ) if 'time_start' in edited or 'time_end' in edited else f"⏰ Время: {format_time(context.user_data['time_start'])} - {format_time(context.user_data['time_end'])}",
        highlight(f"🚘 Марки авто: {context.user_data['car_brand']}" ) if 'car_brand' in edited else f"🚘 Марки авто: {context.user_data['car_brand']}",
        highlight(f"👥 Кол-во людей: {context.user_data['people_count']}" ) if 'people_count' in edited else f"👥 Кол-во людей: {context.user_data['people_count']}",
        highlight(f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}" ) if 'leader_name' in edited else f"👨‍✈️ Позывной старшего: {context.user_data['leader_name']}",
        highlight(f"🔫 Наличие ВВСТ: {context.user_data['cargo']}" ) if 'cargo' in edited else f"🔫 Наличие ВВСТ: {context.user_data['cargo']}",
        highlight(f"💬 Цель перехода: {context.user_data['purpose']}" ) if 'purpose' in edited else f"💬 Цель перехода: {context.user_data['purpose']}"
    ]
    text = '\n'.join(lines)
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return "AWAIT_CONFIRM"

# Новый обработчик для свободной формы заявки
async def free_form_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_blocked(update, context):
        return ConversationHandler.END
    text = update.message.text
    if text == "↩️ Назад":
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    context.user_data['free_form_text'] = text
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_free_form")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_free_form")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_request")]
    ]
    await update.message.reply_text(
        f"Ваша заявка в свободной форме:\n{text}\n\nПроверьте данные и подтвердите отправку заявки.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return "AWAIT_CONFIRM_FREE_FORM"

async def confirm_free_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    # Если нажата кнопка Назад, возвращаемся в главное меню
    if query.data == "↩️ Назад":
        await query.edit_message_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    text = context.user_data.get('free_form_text')
    user_data = {
        'division': '',
        'direction': '',
        'checkpoint': '',
        'date_start': '',
        'date_end': '',
        'time_start': '',
        'time_end': '',
        'car_brand': '',
        'people_count': 0,
        'leader_name': '',
        'cargo': '',
        'purpose': text
    }
    request_id = save_request(user_data, user_id, status=STATUS_NEW)
    if not request_id:
        await query.edit_message_text("Ошибка при сохранении заявки. Попробуйте позже.")
        return ConversationHandler.END
    # Формируем текст и inline-кнопки для администратора
    request = get_request_full(request_id)
    text_admin, keyboard = await get_admin_request_text_and_keyboard(request)
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text_admin, reply_markup=keyboard)
    # Отправляем главное меню новым сообщением
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text = f"Заявка зарегистрирована #{request_id}.\nСтатус: {STATUS_NEW}.\n{context.user_data.get('free_form_text')}\n",
        reply_markup=get_user_reply_keyboard()
    )
    await query.edit_message_reply_markup(reply_markup=None)
    return ConversationHandler.END

async def edit_free_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите новый текст заявки:")
    return "AWAIT_FREE_FORM_INPUT"

# Обработчик входа в редактирование заявки из статуса (для conv_edit)
async def new_request_entry(update, context):
    query = update.callback_query
    await query.answer()
    # Получаем id заявки из user_data (например, context.user_data['status_request_id'])
    request_id = context.user_data.get('status_request_id')
    if request_id:
        from repositories.request_repo import get_request_full
        request = get_request_full(request_id)
        if request:
            # Заполняем user_data для редактирования
            for k in ['division','direction','checkpoint','date_start','date_end','time_start','time_end','car_brand','people_count','leader_name','cargo','purpose']:
                context.user_data[k] = request.get(k)
            context.user_data['edited_fields'] = []
            await query.edit_message_text(
                "Выберите поле для редактирования:",
                reply_markup=get_edit_fields_keyboard()
            )
            return EDIT_FIELD
    await query.edit_message_text(
        "Заявка не найдена или не выбрана.",
        reply_markup=None
    )
    return ConversationHandler.END

# --- Проверка статуса заявки ---
from telegram.ext import ConversationHandler
STATUS_REQUEST_ID = "STATUS_REQUEST_ID"

async def ask_request_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите номер заявки для проверки статуса:")
    return STATUS_REQUEST_ID

async def show_request_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_id = update.message.text.strip()
    request = get_request_full(request_id)
    if not request:
        await update.message.reply_text(
            f"Заявка с номером {request_id} не найдена.",
            reply_markup=get_user_reply_keyboard()
        )
        return ConversationHandler.END
    context.user_data['status_request_id'] = request_id
    text = (
        f"📄 Заявка #{request_id}:\n"
        f"🏢 Подразделение: {request.get('division', '')}\n"
        f"🚧 Направление: {request.get('direction', '')}\n"
        f"🚪 Пункт пропуска: {request.get('checkpoint', '')}\n"
        f"📅 Дата: {request.get('date_start', '')} - {request.get('date_end', '')}\n"
        f"⏰ Время: {request.get('time_start', '')} - {request.get('time_end', '')}\n"
        f"🚘 Марки авто: {request.get('car_brand', '')}\n"
        f"👥 Кол-во людей: {request.get('people_count', '')}\n"
        f"👨‍✈️ Позывной старшего: {request.get('leader_name', '')}\n"
        f"🔫 Наличие ВВСТ: {request.get('cargo', '')}\n"
        f"💬 Цель перехода: {request.get('purpose', '')}\n"
        f"🌟 Статус: {request.get('status', '')}"
    )
    keyboard = [
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit_request"),
            InlineKeyboardButton("🔄 Продублировать", callback_data="duplicate_request")
        ],
        [
            InlineKeyboardButton("❌ Отмена заявки", callback_data="cancel_request"),
            InlineKeyboardButton("↩️ Назад", callback_data="back_to_menu")
        ]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END