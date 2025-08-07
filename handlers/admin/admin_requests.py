# handlers/admin/admin_requests.py
# Обработка заявок: просмотр, фильтрация, действия администратора.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from repositories.request_repo import get_request_full, update_request_status, STATUS_ON_CLARIFICATION, STATUS_CANCELLED, STATUS_IN_PROGRESS, STATUS_DUPLICATED, assign_operator
import asyncio
from handlers.operator.operator_requests import send_request_to_operator
from utils.date_utils import format_date_for_display, format_time_for_display
from db import Database
import logging

logger = logging.getLogger(__name__)

ADMIN_REQUEST_ACTION = 100
ADMIN_OPERATOR_SELECT = 101
ADMIN_REQUEST_REASON = 102

async def get_operators_async():
    """
    Получить список операторов с принудительным обновлением данных из БД.
    Использует прямое соединение с БД для избежания проблем с кэшированием.
    """
    import mysql.connector
    from config import DB_CONFIG, ROLE_OPERATOR
    
    logger.info("[get_operators_async] Начинаем получение операторов...")
    logger.info(f"[get_operators_async] DB_CONFIG: {DB_CONFIG}")
    logger.info(f"[get_operators_async] ROLE_OPERATOR: {ROLE_OPERATOR}")
    
    conn = None
    try:
        # Принудительно создаем новое соединение
        logger.info("[get_operators_async] Создаем новое соединение с БД...")
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn:
            logger.error("[get_operators_async] Нет соединения с БД")
            return []
        
        logger.info("[get_operators_async] Соединение с БД установлено")
        
        with conn.cursor(dictionary=True) as cursor:
            query = "SELECT user_id, username, full_name FROM users WHERE role = %s ORDER BY user_id"
            logger.info(f"[get_operators_async] Выполняем запрос: {query} с параметром {ROLE_OPERATOR}")
            
            cursor.execute(query, (ROLE_OPERATOR,))
            operators = cursor.fetchall()
            
            logger.info(f"[get_operators_async] Получено операторов: {len(operators)}")
            for op in operators:
                logger.info(f"[get_operators_async] Оператор: {op['user_id']} - "
                           f"{op['full_name']} (@{op['username']})")
            
            return operators
    except Exception as e:
        logger.error(f"[get_operators_async] Ошибка: {e}")
        import traceback
        logger.error(f"[get_operators_async] Traceback: {traceback.format_exc()}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("[get_operators_async] Соединение с БД закрыто")

async def get_admin_request_text_and_keyboard(request, show_operators=False):
    # ВСЕГДА получаем актуальные данные заявки из базы
    request = get_request_full(request['id']) if isinstance(request, dict) and 'id' in request else request
    # Получаем список изменённых полей (edited_fields)
    edited_fields = request.get('edited_fields', [])
    if edited_fields is None:
        edited_fields = []
    if isinstance(edited_fields, str):
        edited_fields = [f.strip() for f in edited_fields.split(',') if f.strip()]
    def highlight(text):
        return f"<b><u>{text}</u></b>"
    def format_line(field, label, value):
        return highlight(f"{label}: {value}") if field in edited_fields else f"{label}: {value}"
    # Определяем свободная форма или по образцу
    template_fields = [
        'division', 'direction', 'checkpoint', 'date_start', 'date_end',
        'time_start', 'time_end', 'car_brand', 'people_count',
        'leader_name', 'cargo'
    ]
    is_free_form = all(not request.get(f) for f in template_fields) and request.get('purpose')
    if is_free_form:
        text = (
            f"📄 Заявка #{request['id']}: Статус: {request['status']}\n"
            f"{request.get('purpose', '')}\n" # Текст свободной формы
            f"🆔 ID пользователя: {request.get('user_id', '')}\n"
            f"🥸 Имя пользователя: {request.get('full_name', '')}\n"
        )
        if request['status'] == "Продублировать":
            # Для свободной формы при show_operators=True показываем выбор оператора
            if show_operators:
                operators = await get_operators_async()
                keyboard = [
                    [InlineKeyboardButton(f"{op['full_name']} (@{op['username']})", callback_data=f"duplicate_operator_{op['user_id']}_{request['id']}")]
                    for op in operators
                ]
#                keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data=f"duplicate_cancel_{request['id']}")])
                return text, InlineKeyboardMarkup(keyboard)
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Продублировать", callback_data=f"duplicate_request_{request['id']}")],
                    [InlineKeyboardButton("❌ Отменить", callback_data=f"duplicate_cancel_{request['id']}")]
                ])
                return text, keyboard
    else:
        date_start = format_date_for_display(request.get('date_start', ''))
        date_end = format_date_for_display(request.get('date_end', ''))
        time_start = format_time_for_display(request.get('time_start', ''))
        time_end = format_time_for_display(request.get('time_end', ''))
        date_value = f"{date_start} - {date_end}"
        time_value = f"{time_start} - {time_end}"
        text = (
            f"📄 Заявка #{request['id']}: Статус: {request['status']}\n"
            f"{format_line('division', '🏢 Подразделение', request.get('division', ''))}\n"
            f"{format_line('direction', '🚧 Направление', request.get('direction', ''))}\n"
            f"{format_line('checkpoint', '🚪 Пункт пропуска', request.get('checkpoint', ''))}\n"
            f"{format_line('date_start', '📅 Дата', date_value)}\n"
            f"{format_line('time_start', '⏰ Время', time_value)}\n"
            f"{format_line('car_brand', '🚘 Марки авто', request.get('car_brand', ''))}\n"
            f"{format_line('people_count', '👥 Кол-во людей', request.get('people_count', ''))}\n"
            f"{format_line('leader_name', '👨‍✈️ Позывной старшего', request.get('leader_name', ''))}\n"
            f"{format_line('cargo', '🔫 Наличие ВВСТ', request.get('cargo', ''))}\n"
            f"{format_line('purpose', '💬 Цель перехода', request.get('purpose', ''))}\n"
            f"🆔 ID пользователя: {request.get('user_id', '')}\n"
            f"🥸 Имя пользователя: {request.get('full_name', '')}\n"
        )
        if request['status'] == "Продублировать":
            if show_operators:
                operators = await get_operators_async()
                keyboard = [
                    [InlineKeyboardButton(f"{op['full_name']} (@{op['username']})", callback_data=f"duplicate_operator_{op['user_id']}_{request['id']}")]
                    for op in operators
                ]
               # keyboard.append([InlineKeyboardButton("Отменить", callback_data=f"duplicate_cancel_{request['id']}")])
                return text, InlineKeyboardMarkup(keyboard)
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Продублировать", callback_data=f"duplicate_request_{request['id']}")],
                    [InlineKeyboardButton("❌ Отменить", callback_data=f"duplicate_cancel_{request['id']}")]
                ])
                return text, keyboard
    # Остальные статусы (общие для обеих форм)
    if request['status'] == "Отредактированная":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"edited_approve_{request['id']}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"edited_cancel_{request['id']}")]
        ])
        return text, keyboard
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{request['id']}")],
            [InlineKeyboardButton("❓ Уточнить", callback_data=f"clarify_{request['id']}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{request['id']}")]
        ])
        return text, keyboard

async def admin_requests_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем ID заявки из текста сообщения или callback_data
    request_id = None
    if hasattr(update, 'message') and update.message and update.message.text and update.message.text.isdigit():
        request_id = int(update.message.text)
    elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.data:
        data = update.callback_query.data
        for prefix in ("approve_", "clarify_", "cancel_", "duplicate_operator_", "duplicate_cancel_", "edited_approve_", "edited_cancel_", "edited_operator_"):
            if data.startswith(prefix):
                if data.startswith("duplicate_operator_") or data.startswith("edited_operator_"):
                    request_id = int(data.split('_')[3])
                elif data.startswith("duplicate_cancel_") or data.startswith("edited_cancel_") or data.startswith("edited_approve_"):
                    request_id = int(data.split('_')[2])
                else:
                    request_id = int(data.split('_')[1])
                break
    elif 'request_id' in context.user_data:
        request_id = context.user_data['request_id']
    if request_id:
        request = get_request_full(request_id)
        if request:
            context.user_data['request_data'] = request
        else:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text("Заявка не найдена.")
            else:
                await update.message.reply_text("Заявка не найдена.")
            return ConversationHandler.END
    elif 'request_data' not in context.user_data:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text("Заявка не найдена.")
        else:
            await update.message.reply_text("Заявка не найдена.")
        return ConversationHandler.END
    request = context.user_data['request_data']
    text, keyboard = await get_admin_request_text_and_keyboard(request)
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return ADMIN_REQUEST_ACTION

async def admin_request_action(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"[admin_request_action] === НАЧАЛО ОБРАБОТКИ ===")
    logger.info(f"[admin_request_action] Получен callback: {data}")
    logger.info(f"[admin_request_action] Тип данных: {type(data)}")
    logger.info(f"[admin_request_action] User ID: {update.effective_user.id}")
    logger.info(f"[admin_request_action] Chat ID: {update.effective_chat.id}")
    
    # Принудительно очищаем кэш операторов при каждом вызове
    if hasattr(context, 'operators_cache'):
        delattr(context, 'operators_cache')
        logger.info("[admin_request_action] Очищен context.operators_cache")
    
    # Принудительно очищаем user_data кэш операторов
    if 'operators_cache' in context.user_data:
        del context.user_data['operators_cache']
        logger.info("[admin_request_action] Очищен context.user_data['operators_cache']")
    
    if data.startswith("approve_"):
        logger.info(f"[admin_request_action] === ОБРАБОТКА APPROVE ===")
        request_id = int(data.split('_')[1])
        logger.info(f"[admin_request_action] Обрабатываем approve для заявки {request_id}")
        
        # Получаем заявку из БД
        request = get_request_full(request_id)
        if not request:
            logger.error(f"[admin_request_action] Заявка {request_id} не найдена в БД")
            await query.edit_message_text("Заявка не найдена в базе данных.")
            return ConversationHandler.END
        
        logger.info(f"[admin_request_action] Заявка {request_id} найдена, статус: {request.get('status')}")
        context.user_data['request_data'] = request
        
        # Принудительно получаем свежих операторов
        logger.info("[admin_request_action] Начинаем получение операторов...")
        operators = await get_operators_async()
        logger.info(f"[admin_request_action] Получено операторов: {len(operators)}")
        
        if not operators:
            logger.warning("[admin_request_action] Нет доступных операторов")
            await query.edit_message_text("Нет доступных операторов.")
            return ConversationHandler.END
        
        # Формируем список операторов для отображения
        op_list = "\n".join([f"{op['full_name']} (@{op['username']})" for op in operators])
        msg = f"Выберите оператора для назначения заявки:\n\nНайдено операторов: {len(operators)}\n{op_list}"
        
        # Создаем клавиатуру
        keyboard = []
        for op in operators:
            callback_data = f"operator_{op['user_id']}_{request_id}"
            logger.info(f"[admin_request_action] Создаем кнопку для оператора {op['user_id']} с callback_data: {callback_data}")
            keyboard.append([InlineKeyboardButton(f"{op['full_name']} (@{op['username']})", callback_data=callback_data)])
        
        logger.info(f"[admin_request_action] Создана клавиатура с {len(keyboard)} кнопками")
        
        try:
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
            logger.info("[admin_request_action] Сообщение успешно обновлено")
            return ADMIN_OPERATOR_SELECT
        except Exception as e:
            logger.error(f"[admin_request_action] Ошибка при обновлении сообщения: {e}")
            await query.edit_message_text(f"Ошибка при обновлении сообщения: {e}")
            return ConversationHandler.END
    elif data.startswith("edited_approve_"):
        request_id = int(data.split('_')[2])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        operators = await get_operators_async()
        if not operators:
            await query.edit_message_text("Нет доступных операторов.")
            return ConversationHandler.END
        keyboard = [
            [InlineKeyboardButton(f"{op['full_name']} (@{op['username']})", callback_data=f"edited_operator_{op['user_id']}_{request_id}")]
            for op in operators
        ]
        await query.edit_message_text("Выберите оператора для назначения заявки:", reply_markup=InlineKeyboardMarkup(keyboard))
        return ADMIN_OPERATOR_SELECT
    elif data.startswith("clarify_"):
        request_id = int(data.split('_')[1])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        context.user_data['reason_type'] = STATUS_ON_CLARIFICATION
        await query.edit_message_text("Введите причину уточнения заявки:")
        return ADMIN_REQUEST_REASON
    elif data.startswith("cancel_"):
        request_id = int(data.split('_')[1])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        context.user_data['reason_type'] = STATUS_CANCELLED
        await query.edit_message_text("Введите причину отмены заявки:")
        return ADMIN_REQUEST_REASON
    elif data.startswith("edited_operator_"):
        parts = data.split('_')
        operator_id = int(parts[2])
        request_id = int(parts[3])
        assign_operator(request_id, operator_id)
        # Статус заявки остается 'Отредактированная'
        request = get_request_full(request_id)
        user_id = request.get('user_id')
        operators = await get_operators_async()
        operator = next((op for op in operators if op['user_id'] == operator_id), None)
        operator_name = operator['full_name'] if operator else f"Оператор {operator_id}"
        await send_request_to_operator(context, operator_id, request_id)
        await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} передана оператору.")
#        await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} передана оператору: {operator_name}.")
        await query.edit_message_text(f"Заявка отправлена оператору: {operator_name}.")
        return ConversationHandler.END
    elif data.startswith("duplicate_request_"):
        request_id = int(data.split('_')[2])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        # Показываем подменю операторов
        text, keyboard = await get_admin_request_text_and_keyboard(request, show_operators=True)
        await query.edit_message_text("Выберите оператора для назначения заявки:", reply_markup=keyboard)
        return ADMIN_OPERATOR_SELECT
    elif data.startswith("duplicate_operator_"):
        parts = data.split('_')
        operator_id = int(parts[2])
        request_id = int(parts[3])
        assign_operator(request_id, operator_id)
        update_request_status(request_id, "Продублировать")
        # После назначения оператора, всегда брать заявку из базы
        request = get_request_full(request_id)
        user_id = request.get('user_id')
        operators = await get_operators_async()
        operator = next((op for op in operators if op['user_id'] == operator_id), None)
        operator_name = operator['full_name'] if operator else f"Оператор {operator_id}"
        await send_request_to_operator(context, operator_id, request_id)
        await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} продублирована оператору.")
#        await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} продублирована оператору: {operator_name}.")
        await query.edit_message_text(f"Заявка отправлена оператору: {operator_name}.")
        return ConversationHandler.END
    elif data.startswith("duplicate_cancel_"):
        request_id = int(data.split('_')[2])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        await query.edit_message_text("Введите причину отмены продублированной заявки:")
        context.user_data['reason_type'] = STATUS_CANCELLED
        return ADMIN_REQUEST_REASON
    elif data.startswith("edited_cancel_"):
        request_id = int(data.split('_')[2])
        request = get_request_full(request_id)
        context.user_data['request_data'] = request
        context.user_data['reason_type'] = STATUS_CANCELLED
        await query.edit_message_text("Введите причину отмены отредактированной заявки:")
        return ADMIN_REQUEST_REASON
    await query.edit_message_text("Ошибка выбора действия.")
    return ConversationHandler.END

async def admin_operator_select(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"[admin_operator_select] === НАЧАЛО ОБРАБОТКИ ===")
    logger.info(f"[admin_operator_select] Получен callback: {data}")
    logger.info(f"[admin_operator_select] Тип данных: {type(data)}")
    
    # Проверяем, что data действительно начинается с operator_ и далее идет id
    if data.startswith("operator_"):
        logger.info(f"[admin_operator_select] === ОБРАБОТКА OPERATOR ===")
        parts = data.split('_')
        logger.info(f"[admin_operator_select] Части callback: {parts}")
        
        # Проверяем, что parts[1] действительно число (user_id), а parts[2] - request_id
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            operator_id = int(parts[1])
            request_id = int(parts[2])
            logger.info(f"[admin_operator_select] Operator ID: {operator_id}, Request ID: {request_id}")
            
            request = get_request_full(request_id)
            if not request:
                logger.error(f"[admin_operator_select] Заявка {request_id} не найдена")
                await query.edit_message_text("Заявка не найдена.")
                return ConversationHandler.END
            
            user_id = request.get('user_id')
            logger.info(f"[admin_operator_select] User ID: {user_id}")
            
            assign_operator(request_id, operator_id)
            update_request_status(request_id, STATUS_IN_PROGRESS)
            
            operators = await get_operators_async()
            operator = next((op for op in operators if op['user_id'] == operator_id), None)
            operator_name = operator['full_name'] if operator else f"Оператор {operator_id}"
            logger.info(f"[admin_operator_select] Оператор: {operator_name}")
            
            # Отправляем заявку оператору со всеми полями
            await send_request_to_operator(context, operator_id, request_id)
            await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} принята в работу оператором.")
            await query.edit_message_text(f"Заявка отправлена оператору: {operator_name}.")
            logger.info(f"[admin_operator_select] Заявка успешно отправлена оператору")
            return ConversationHandler.END
        else:
            logger.error(f"[admin_operator_select] Неверный формат callback: {data}")
            # Не обрабатываем confirm/cancel и другие callback'и здесь, чтобы не было ValueError
            return ConversationHandler.END
    elif data.startswith("edited_operator_"):
        parts = data.split('_')
        if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
            operator_id = int(parts[2])
            request_id = int(parts[3])
            assign_operator(request_id, operator_id)
            # Статус заявки остается 'Отредактированная'
            request = get_request_full(request_id)
            user_id = request.get('user_id')
            operators = await get_operators_async()
            operator = next((op for op in operators if op['user_id'] == operator_id), None)
            operator_name = operator['full_name'] if operator else f"Оператор {operator_id}"
            await send_request_to_operator(context, operator_id, request_id)
            await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} передана оператору.")
#            await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request_id} передана оператору: {operator_name}.")
            await query.edit_message_text(f"Заявка отправлена оператору: {operator_name}.")
            return ConversationHandler.END
        else:
            return ConversationHandler.END
    # Не обрабатываем другие callback'и, чтобы не было ValueError
    return ConversationHandler.END

async def admin_request_reason(update, context):
    reason = update.message.text
    request = context.user_data.get('request_data')
    user_id = request.get('user_id')
    reason_type = context.user_data.get('reason_type')
    update_request_status(request['id'], reason_type, reason)
    if reason_type == STATUS_ON_CLARIFICATION:
        from handlers.edit_request import format_request_text
        text = f"Ваша заявка #{request['id']} отправлена на уточнение.\nПричина: {reason}\n\n" + format_request_text(request)
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=user_id, text=f"Ваша заявка #{request['id']} отменена. Причина: {reason}")
    await update.message.reply_text("Причина отправлена пользователю.")
    return ConversationHandler.END

async def notify_admins_about_duplicate(context, request_id, admin_ids):
    """
    Отправляет заявку со статусом 'Продублировать' всем администраторам с inline-кнопками.
    """
    request = get_request_full(request_id)
    text, keyboard = await get_admin_request_text_and_keyboard(request)
    for admin_id in admin_ids:
        await context.bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard, parse_mode="HTML")

async def notify_admins_about_edited(context, request_id, admin_ids):
    """
    Отправляет заявку со статусом 'Отредактированная' всем администраторам с inline-кнопками.
    """
    request = get_request_full(request_id)
    text, keyboard = await get_admin_request_text_and_keyboard(request)
    for admin_id in admin_ids:
        await context.bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard, parse_mode="HTML")

async def simple_approve_handler(update, context):
    """Упрощенный обработчик для кнопки 'Подтвердить'"""
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"[simple_approve_handler] Получен callback: {data}")
    
    if data.startswith("approve_"):
        request_id = int(data.split('_')[1])
        logger.info(f"[simple_approve_handler] Обрабатываем approve для заявки {request_id}")
        
        # Простое сообщение для тестирования
        await query.edit_message_text(f"Тест: кнопка 'Подтвердить' работает для заявки {request_id}")
        return ConversationHandler.END
    
    return ConversationHandler.END
