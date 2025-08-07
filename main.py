# main.py
# Главный файл запуска Telegram-бота для подачи и обработки заявок.
# Здесь настраиваются обработчики команд, диалогов и запускается polling.

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config import TOKEN, MENU, DIVISION, DIRECTION, CHECKPOINT, DATE_START, DATE_END, TIME_START, TIME_END, CAR_BRAND, PEOPLE_COUNT, LEADER_NAME, CARGO, PURPOSE, ADMIN_CHAT_ID
from handlers.start import start, cancel, user_menu_create_request
from handlers.new_request import new_request, date_start, date_end, handle_time, car_brand, people_count, manual_people_count, leader_name, cargo, purpose, free_form_request, confirm_request, edit_request, confirm_free_form, edit_free_form, edit_field, after_edit as after_edit_new, EDIT_FIELD, division_create, direction_create, checkpoint_create, cancel_request as cancel_new_request
from handlers.edit_request import edit_request_entry, division_edit, direction_edit, checkpoint_edit, date_start_edit, date_end_edit, time_start_edit, time_end_edit, car_brand_edit, people_count_edit, leader_name_edit, cargo_edit, purpose_edit, duplicate_request, back_to_menu, back_to_actions, select_request, confirm_edit, after_free_form_edit, after_edit, cancel_request as cancel_existing_request
from handlers.status import ask_request_id, show_request_status
from handlers.new_request import new_request_entry
from keyboards.main_menu import handle_back
from handlers.admin.conv_admin import conv_admin
from handlers.admin.admin_requests import admin_request_action, admin_operator_select, admin_request_reason, ADMIN_REQUEST_ACTION, ADMIN_OPERATOR_SELECT, ADMIN_REQUEST_REASON
from handlers.admin.admin_commands import (
    admin_restart_command, admin_hard_restart_command, 
    admin_broadcast_command, show_users_command, refresh_operators_command
)
from handlers.operator.operator_requests import (
    operator_request_action, operator_request_reason,
    operator_view_requests, operator_view_menu,
    operator_view_leader, operator_view_id,
    OPERATOR_REQUEST_ACTION, OPERATOR_REQUEST_REASON, OPERATOR_VIEW_MENU, OPERATOR_VIEW_LEADER, OPERATOR_VIEW_ID
)

logger = logging.getLogger(__name__)

# Обработчик выбора способа создания заявки
async def menu_choice(update, context):
    text = update.message.text
    if text == "🧾 По образцу":
        return await new_request(update, context)
    elif text == "🗒 В свободной форме":
        await update.message.reply_text(
        "Введите данные согласно рекомендациям:\n"
        "🏢 Подразделение:\n"
        "🚧 Направление:\n"
        "🚪 Пункт пропуска:\n"
        "📅 Дата (ДД.ММ - ДД.ММ):\n"
        "⏰ Время (ЧЧ:ММ - ЧЧ:ММ):\n"
        "🚘 Марки авто и кол-во (КамАЗ -1):\n"
        "👥 Кол-во людей:\n"
        "👨‍✈️ Позывной старшего:\n"
        "🔫 Наличие ВВСТ (Оружие, Техника):\n"
        "💬 Цель перехода:\n"
        "👇👇👇👇👇👇👇👇")
        return "AWAIT_FREE_FORM_INPUT"
    elif text == "↩️ Назад":
        from keyboards.main_menu import get_reply_keyboard
        from config import ROLE_USER
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_reply_keyboard(context.user_data.get('role', ROLE_USER))
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, выберите вариант из меню.")
        return MENU

# Точка входа: настройка приложения и запуск polling
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('cancel', cancel))
    app.add_handler(CommandHandler('restart', admin_restart_command))
    app.add_handler(CommandHandler('hard_restart', admin_hard_restart_command))
    app.add_handler(CommandHandler('broadcast', admin_broadcast_command))
    app.add_handler(CommandHandler('show_users', show_users_command))
    app.add_handler(CommandHandler('refresh_operators', refresh_operators_command))
    
    # ConversationHandler для обработки действий оператора (подтвердить/отменить/продублировать)
    conv_operator_action = ConversationHandler(
        entry_points=[CallbackQueryHandler(operator_request_action, pattern=r"^operator_confirm_\d+$|^operator_cancel_\d+$|^operator_duplicate_\d+$")],
        states={
            OPERATOR_REQUEST_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, operator_request_reason)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_operator_action)

    # ConversationHandler для просмотра заявок оператором
    conv_operator_view = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🔍 Просмотр заявок"]), operator_view_requests)],
        states={
            OPERATOR_VIEW_MENU: [CallbackQueryHandler(operator_view_menu)],
            OPERATOR_VIEW_LEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, operator_view_leader)],
            OPERATOR_VIEW_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, operator_view_id)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_operator_view)
    # ConversationHandler для создания заявки (по образцу)
    conv_create = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🆕 Создать заявку"]), user_menu_create_request)],
        states={
            MENU: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, free_form_request)],
            "AWAIT_FREE_FORM_INPUT": [MessageHandler(filters.TEXT & ~filters.COMMAND, free_form_request)],
            DIVISION: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, division_create)],
            DIRECTION: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(direction_create)],
            CHECKPOINT: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(checkpoint_create)],
            DATE_START: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(date_start)],
            DATE_END: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(date_end)],
            TIME_START: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(handle_time, pattern="^time_start_")],
            TIME_END: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(handle_time, pattern="^time_end_")],
            CAR_BRAND: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_brand)],
            PEOPLE_COUNT: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                CallbackQueryHandler(people_count),
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_people_count)],
            LEADER_NAME: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, leader_name)],
            CARGO: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, cargo)],
            PURPOSE: [
                MessageHandler(filters.Text(["↩️ Назад"]), handle_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, purpose)],
            "AWAIT_CONFIRM": [
                CallbackQueryHandler(confirm_request, pattern="^confirm_request$"),
                CallbackQueryHandler(edit_request, pattern="^edit_request$"),
                CallbackQueryHandler(cancel_new_request, pattern="^cancel_request$")],
            "AWAIT_CONFIRM_FREE_FORM": [
                CallbackQueryHandler(confirm_free_form, pattern="^confirm_free_form$"),
                CallbackQueryHandler(edit_free_form, pattern="^edit_free_form$"),
                CallbackQueryHandler(cancel_new_request, pattern="^cancel_request$")],
            "CONFIRM_EDIT": [
                CallbackQueryHandler(confirm_edit, pattern="^confirm_edit$"),
                CallbackQueryHandler(edit_request, pattern="^edit_request$"),
                CallbackQueryHandler(cancel_new_request, pattern="^cancel_request$")],
            EDIT_FIELD: [
                CallbackQueryHandler(edit_field, pattern="^edit_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, after_edit_new)]
        },
        fallbacks=[CommandHandler('cancel', cancel_new_request)]
    )
    app.add_handler(conv_create)
    # ConversationHandler для проверки статуса и редактирования заявки
    conv_edit = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🔍 Проверить статус"]), ask_request_id)],
        states={
            "STATUS_REQUEST_ID": [MessageHandler(filters.TEXT & ~filters.COMMAND, show_request_status)],
            "STATUS_ACTION": [
                CallbackQueryHandler(edit_request_entry, pattern="^edit_request$"),
                CallbackQueryHandler(cancel_existing_request, pattern="^cancel_request$"),
                CallbackQueryHandler(duplicate_request, pattern="^duplicate_request$"),
                CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"),
                CallbackQueryHandler(back_to_actions, pattern="^back_to_actions$"),
                CallbackQueryHandler(select_request, pattern="^select_request$"),],
            EDIT_FIELD: [
                CallbackQueryHandler(edit_field, pattern="^edit_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, after_edit)],
            DIVISION: [MessageHandler(filters.TEXT & ~filters.COMMAND, division_edit)],
            DIRECTION: [
                CallbackQueryHandler(direction_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, direction_edit)],
            CHECKPOINT: [
                CallbackQueryHandler(checkpoint_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, checkpoint_edit)],
            DATE_START: [
                CallbackQueryHandler(date_start_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, date_start_edit)],
            DATE_END: [
                CallbackQueryHandler(date_end_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, date_end_edit)],
            TIME_START: [
                CallbackQueryHandler(time_start_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, time_start_edit)],
            TIME_END: [
                CallbackQueryHandler(time_end_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, time_end_edit)],
            CAR_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_brand_edit)],
            PEOPLE_COUNT: [
                CallbackQueryHandler(people_count_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, people_count_edit)],
            LEADER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, leader_name_edit)],
            CARGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, cargo_edit)],
            PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purpose_edit)],
            "AWAIT_CONFIRM": [
                CallbackQueryHandler(confirm_request, pattern="^confirm_edit$"),
                CallbackQueryHandler(new_request_entry, pattern="^edit_request$"),
                CallbackQueryHandler(edit_request_entry, pattern="^edit_request$"),
                CallbackQueryHandler(cancel_existing_request, pattern="^cancel_request$")],
            "CONFIRM_EDIT": [
                CallbackQueryHandler(confirm_edit, pattern="^confirm_edit$"),
                CallbackQueryHandler(edit_request_entry, pattern="^edit_request$"),
                CallbackQueryHandler(back_to_actions, pattern="^back_to_actions$")],
            "AWAIT_FREE_FORM_EDIT": [MessageHandler(filters.TEXT & ~filters.COMMAND, after_free_form_edit)]
        },
        fallbacks=[CommandHandler('cancel', cancel_existing_request)]
    )
    app.add_handler(conv_edit)
    
    # Отдельный обработчик для approve_ и edited_approve_ callback'ов
    async def approve_handler(update, context):
        """Обработчик для кнопки 'Подтвердить'"""
        query = update.callback_query
        data = query.data
        logger.info(f"[approve_handler] Получен callback: {data}")
        
        if data.startswith("approve_") or data.startswith("edited_approve_"):
            # Импортируем функцию здесь, чтобы избежать циклических импортов
            from handlers.admin.admin_requests import admin_request_action
            return await admin_request_action(update, context)
        
        # Если это не approve_ или edited_approve_, передаем управление дальше
        return False
    
    # Отдельный обработчик для operator_ и edited_operator_ callback'ов
    async def operator_handler(update, context):
        """Обработчик для выбора оператора"""
        query = update.callback_query
        data = query.data
        logger.info(f"[operator_handler] Получен callback: {data}")
        
        if data.startswith("operator_") or data.startswith("edited_operator_"):
            # Импортируем функцию здесь, чтобы избежать циклических импортов
            from handlers.admin.admin_requests import admin_operator_select
            return await admin_operator_select(update, context)
        
        # Если это не operator_ или edited_operator_, передаем управление дальше
        return False
    
    app.add_handler(CallbackQueryHandler(approve_handler, pattern="^(approve_|edited_approve_)"))
    app.add_handler(CallbackQueryHandler(operator_handler, pattern="^(operator_|edited_operator_)"))
    
    app.add_handler(conv_admin)  # Добавлен обработчик администратора
    app.add_handler(MessageHandler(filters.Text(["Главное меню"]), user_menu_create_request))
    
    # Глобальный обработчик для диагностики всех callback'ов
    async def global_callback_handler(update, context):
        """Глобальный обработчик для диагностики всех callback'ов"""
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            data = query.data
            logger.info(f"[GLOBAL CALLBACK] {data}")
            # Не отвечаем на callback, чтобы другие обработчики могли его обработать
    
    app.add_handler(CallbackQueryHandler(global_callback_handler))
    
    app.run_polling()

if __name__ == '__main__':
    main()
