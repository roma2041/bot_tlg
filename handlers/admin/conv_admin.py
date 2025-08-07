# handlers/admin/conv_admin.py
# ConversationHandler для админского меню

from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from keyboards.admin.menu import get_admin_main_menu, get_admin_manage_menu, get_admin_requests_menu, get_admin_export_menu
from handlers.admin.admin_menu import admin_main_entry, admin_manage_entry
from handlers.admin.admin_users import admin_users_entry, admin_user_id, admin_user_action, admin_role_select
from handlers.admin.admin_requests import admin_requests_entry, admin_request_action, admin_operator_select, admin_request_reason
from handlers.admin.admin_export import admin_export_entry
from handlers.admin.states import ADMIN_MAIN, ADMIN_MANAGE, ADMIN_USERS, ADMIN_REQUESTS, ADMIN_EXPORT, ADMIN_USER_ID, ADMIN_USER_ACTION, ADMIN_ROLE_SELECT, ADMIN_REQUEST_REASON, ADMIN_REQUEST_ACTION, ADMIN_OPERATOR_SELECT
import logging

logger = logging.getLogger(__name__)

conv_admin = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Text(["Администрирование", "Выгрузка заявок в Excel"]), admin_main_entry),
        CallbackQueryHandler(admin_request_action, pattern="^(approve_|clarify_|cancel_|duplicate_operator_|duplicate_cancel_|duplicate_request_|edited_approve_|edited_cancel_|edited_operator_)") ,
        CallbackQueryHandler(admin_operator_select, pattern="^(operator_|edited_operator_)")
    ],
    states={
        ADMIN_MAIN: [
            MessageHandler(filters.Text(["Администрирование"]), admin_manage_entry),
            MessageHandler(filters.Text(["Выгрузка заявок в Excel"]), admin_export_entry),
        ],
        ADMIN_MANAGE: [
            MessageHandler(filters.Text(["Пригласить (заглушка)"]), admin_manage_entry),
            MessageHandler(filters.Text(["Управление пользователями"]), admin_users_entry),
            MessageHandler(filters.Text(["↩️ Назад"]), admin_main_entry),
        ],
        ADMIN_USERS: [
            MessageHandler(filters.Text(["↩️ Назад"]), admin_manage_entry),
        ],
        ADMIN_USER_ID: [
            MessageHandler(filters.TEXT & (~filters.COMMAND), admin_user_id),
        ],
        ADMIN_USER_ACTION: [
            CallbackQueryHandler(admin_user_action),
        ],
        ADMIN_ROLE_SELECT: [
            CallbackQueryHandler(admin_role_select),
        ],
        ADMIN_REQUESTS: [
            MessageHandler(filters.Text(["Проверка статуса заявки"]), admin_requests_entry),
            MessageHandler(filters.Text(["↩️ Назад"]), admin_main_entry),
            CallbackQueryHandler(admin_requests_entry, pattern="^(duplicate_operator_|duplicate_cancel_)") ,
            CallbackQueryHandler(admin_request_action, pattern="^duplicate_request_"),
            CallbackQueryHandler(admin_operator_select, pattern="^(duplicate_operator_|operator_|edited_operator_)")
        ],
        ADMIN_EXPORT: [
            MessageHandler(filters.Text(["За все время"]), admin_export_entry),
            MessageHandler(filters.Text(["За период"]), admin_export_entry),
            MessageHandler(filters.Text(["↩️ Назад"]), admin_main_entry),
        ],
        ADMIN_REQUEST_ACTION: [
            CallbackQueryHandler(admin_request_action, pattern="^(approve_|clarify_|cancel_|duplicate_operator_|duplicate_cancel_|duplicate_request_|edited_approve_|edited_cancel_|edited_operator_)") ,
            MessageHandler(filters.TEXT & (~filters.COMMAND), admin_requests_entry),
        ],
        ADMIN_REQUEST_REASON: [MessageHandler(filters.TEXT & (~filters.COMMAND), admin_request_reason)],
        ADMIN_OPERATOR_SELECT: [
            CallbackQueryHandler(admin_operator_select, pattern="^(operator_|edited_operator_)") ,
            CallbackQueryHandler(admin_request_action, pattern="^duplicate_operator_")
        ],
    },
    fallbacks=[MessageHandler(filters.Text(["↩️ Назад"]), admin_main_entry)]
)

# Добавляем логирование для диагностики
logger.info("[conv_admin] ConversationHandler создан")
logger.info("[conv_admin] Entry points настроены для approve_, clarify_, cancel_ и других callback'ов")
