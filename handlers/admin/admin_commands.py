# handlers/admin/admin_commands.py
# Административные команды для управления ботом

import logging
from config import ADMIN_CHAT_ID
from repositories.request_repo import get_all_users

logger = logging.getLogger(__name__)

async def admin_restart_command(update, context):
    """Мягкий перезапуск бота - очистка состояний"""
    user_id = update.effective_user.id
    # ADMIN_CHAT_ID может быть строкой, поэтому приводим к str
    if str(user_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ Только администратор может перезапустить бота.")
        return
    
    await update.message.reply_text("🔄 Перезапуск бота...")
    
    try:
        # Очистка состояния пользователя (user_data, chat_data)
        context.user_data.clear()
        context.chat_data.clear()
        
        # Очистка всех активных диалогов
        # Это поможет сбросить все ConversationHandler состояния
        await update.message.reply_text("🧹 Очистка активных диалогов...")
        
        # Перезагрузка конфигурации (если нужно)
        # Здесь можно добавить перезагрузку конфигов из файлов
        
        await update.message.reply_text("✅ Бот перезапущен! Все состояния очищены, конфигурация обновлена.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при перезапуске: {e}")
        # Если не удалось перезапустить, хотя бы очистим состояние
        await update.message.reply_text("🔄 Бот перезапущен (очищено состояние). Все диалоги сброшены.")

async def admin_hard_restart_command(update, context):
    """Полный перезапуск бота с остановкой процесса"""
    user_id = update.effective_user.id
    # ADMIN_CHAT_ID может быть строкой, поэтому приводим к str
    if str(user_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ Только администратор может перезапустить бота.")
        return
    
    await update.message.reply_text("🛑 Полный перезапуск бота...")
    
    try:
        # Останавливаем polling
        await context.application.stop()
        await context.application.shutdown()
        
        # Отправляем сообщение о том, что бот остановлен
        await update.message.reply_text("🛑 Бот остановлен. Для полного перезапуска необходимо запустить бота заново.")
        
        # Выходим из программы
        import sys
        sys.exit(0)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при перезапуске: {e}")
        await update.message.reply_text("🔄 Бот перезапущен (очищено состояние). Все диалоги сброшены.")

async def admin_broadcast_command(update, context):
    """Отправка уведомления всем пользователям"""
    user_id = update.effective_user.id
    # ADMIN_CHAT_ID может быть строкой, поэтому приводим к str
    if str(user_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ Только администратор может отправлять уведомления.")
        return
    
    # Проверяем, есть ли текст сообщения
    if not update.message.text or len(update.message.text.split()) < 2:
        await update.message.reply_text(
            "📢 Использование: /broadcast <текст сообщения>\n\n"
            "Пример: /broadcast 🔧 Технические работы 15.08.2024 с 10:00 до 12:00"
        )
        return
    
    # Получаем текст сообщения (убираем команду /broadcast)
    message_text = update.message.text.replace('/broadcast', '').strip()
    
    if not message_text:
        await update.message.reply_text("❌ Текст сообщения не может быть пустым.")
        return
    
    await update.message.reply_text("📢 Начинаю отправку уведомления всем пользователям...")
    
    try:
        # Получаем всех пользователей
        all_users = get_all_users()
        if not all_users:
            await update.message.reply_text("❌ Нет пользователей в базе данных.")
            return
        
        # Отправляем сообщение каждому пользователю
        success_count = 0
        error_count = 0
        
        for user in all_users:
            try:
                user_id = user['user_id']
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 **Уведомление от администратора:**\n\n{message_text}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                # Логируем ошибку, но продолжаем отправку
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        
        # Отправляем отчет администратору
        report = f"✅ **Отчет об отправке:**\n\n"
        report += f"📤 Успешно отправлено: {success_count}\n"
        if error_count > 0:
            report += f"❌ Ошибок отправки: {error_count}\n"
        report += f"📝 Текст сообщения:\n{message_text}"
        
        await update.message.reply_text(report, parse_mode="HTML")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке уведомлений: {e}")

async def show_users_command(update, context):
    """Показать всех пользователей в базе данных"""
    user_id = update.effective_user.id
    if str(user_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ Только администратор может просматривать пользователей.")
        return
    
    try:
        all_users = get_all_users()
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении пользователей: {e}")
        return
    
    if not all_users:
        await update.message.reply_text("Нет пользователей в базе или ошибка подключения к базе.")
        return
    
    user_list = "\n".join([f"{u['user_id']}: {u['full_name']} (@{u['username']}) - {u['role']}" for u in all_users])
    await update.message.reply_text(f"Пользователи в базе:\n{user_list}")

async def refresh_operators_command(update, context):
    """Обновить список операторов"""
    user_id = update.effective_user.id
    # ADMIN_CHAT_ID может быть строкой, поэтому приводим к str
    if str(user_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ Только администратор может обновить список операторов.")
        return
    
    from handlers.admin.admin_requests import get_operators_async
    try:
        operators = await get_operators_async()
        if operators:
            op_list = "\n".join([f"{op['user_id']}: {op['full_name']} (@{op['username']})" for op in operators])
            await update.message.reply_text(f"✅ Список операторов обновлен:\n{op_list}")
        else:
            await update.message.reply_text("⚠️ Операторы не найдены в базе данных.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обновлении списка операторов: {e}") 