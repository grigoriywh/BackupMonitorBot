import os
import re
import time
import asyncio
from functools import partial
from datetime import datetime, timedelta
import configparser
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ApplicationBuilder
from telegram.error import BadRequest
from telegram.error import NetworkError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from config import read_config, write_backup_path, write_chat_id, get_config_values, reload_config
from logging_config import logger
from backup_manager import (
    read_backup_path,
    parse_backup_filename,
    get_latest_backups,
    get_today_backups,
    get_backup_history,
    format_backup_status,
    format_backup_status_mobile,
    notify_backup_command,
    notify_backup_status,
    mtoday_backup_status,
    mbackup_status,
    backup_history,
    today_backup_status,
    backup_status
)

config = read_config()
BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, CHAT_ID, TIME_NOTIFICATION = get_config_values()

TIMEZONE = "МСК"

TOKEN = ""
bot = Bot(TOKEN)

# Функция, которая будет выполняться при команде /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "Приветствую! Я бот для мониторинга резервных копий от компании ООО \"Инфосфера\".\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "       Мониторинг резевных копий\n"
        "/backupstatus - Статус всех резервных копий\n"
        "/todaybackupstatus - Резервные копии за сегодня\n"
        "/history <сервер> - История резервных копий сервера\n"
        "       Мониторинг резевных копий (формат для android)\n"
        "/mbackupstatus - Статус резервных копий (моб. версия)\n"
        "/mtodaybackupstatus - Резервные копии за сегодня (моб. версия)\n"
        "       Системные команды\n"
        "/config - Показать настройки конфигурации\n"
        "/getgroupid - Получить и сохранить ID группы\n"
        "/reloadconfig - Обновить информацию из файла config.ini\n\n"
        
        "    Ежедневное оповещение ✅\n"
        "/notify - Отправить уведомление о статусе резервных копий\n\n"
        "Бот ежедневно отправляет уведомления о статусе резервных копий, приоритет мониторинга в наличии бэкапов на конец предыдущего рабочего дня клиента. Соответственно, бэкапы проверяются начиная с 15:00 предыдущего дня."
    )
    if update.message:
        await update.message.reply_text(message)
    else:
        logger.error("No message in update")
    
# Асинхронная функция для обработки команды /reloadconfig
async def reload_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reload_config()
    await update.message.reply_text("Конфигурация перезагружена. Чтобы изменить время ежедневного задания, необходимо внести изменения в файл config.ini и перезапустить бота.")

# Асинхронная функция для обработки команды /config
async def config_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    backup_path_file, server_list_allowed, server_list_disallowed, chat_id, time_notification = get_config_values()

    message = (
        f"Файл config.ini\n\n"
        f"[Paths]\n"
        f"backup_path_file = {backup_path_file}\n\n"
        f"[Servers]\n"
        f"server_list_allowed = {', '.join(server_list_allowed)}\n"
        f"server_list_disallowed = {', '.join(server_list_disallowed)}\n\n"
        f"[Notification]\n"
        f"CHAT_ID = {chat_id}\n"
        f"TIME_NOTIFICATION = {time_notification}\n"
    )

    await update.message.reply_text(message)

# Функция для получения ID группы и записи в конфигурационный файл
async def get_group_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    write_chat_id(chat_id)
    await update.message.reply_text(f"ID этой группы: {chat_id} записан в config.ini")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    if update and update.effective_message:
        text = "Произошла ошибка при обработке вашего запроса."
        await update.effective_message.reply_text(text)

#async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #await update.message.reply_text(update.message.text)

async def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build() # telegram\ext_applicationbuilder.py:327: PTBUserWarning: Application instances should be built via the ApplicationBuilder.

    # Настройка планировщика задач
    scheduler = AsyncIOScheduler()

    # Чтение времени уведомления из конфигурационного файла
    try:
        notification_time_str = config['Notification']['TIME_NOTIFICATION']
        notification_time = datetime.strptime(notification_time_str, '%H:%M:%S').time()
    except KeyError:
        logger.error("Ключ 'TIME_NOTIFICATION' не найден в секции 'Notification' конфигурационного файла.")
        return
    except ValueError:
        logger.error("Неправильный формат времени в 'TIME_NOTIFICATION'. Ожидается формат HH:MM:SS.")
        return

    # Чтение chat_id из конфигурационного файла
    try:
        chat_id = config['Notification']['CHAT_ID']
    except KeyError:
        logger.error("Ключ 'CHAT_ID' не найден в секции 'Notification' конфигурационного файла.")
        return

    # Функция для вызова уведомления через планировщик
    async def scheduled_notify_backup_status(context: ContextTypes.DEFAULT_TYPE) -> None:
        await notify_backup_status(context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, CHAT_ID, logger)

    scheduled_notify_backup_status = partial(
        notify_backup_status,
        BACKUP_PATH_FILE=BACKUP_PATH_FILE,
        SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED,
        SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED,
        CHAT_ID=CHAT_ID,
        logger=logger
    )

    # Запуск уведомления в указанное время каждый день
    scheduler.add_job(
        scheduled_notify_backup_status,
        trigger='cron',
        hour=notification_time.hour,
        minute=notification_time.minute,
        second=notification_time.second,
        kwargs={"context": {"application": application}}
    )

    scheduler.start()

    # обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("backupstatus", partial(backup_status, BACKUP_PATH_FILE=BACKUP_PATH_FILE, SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED, TIMEZONE=TIMEZONE, logger=logger)))
    application.add_handler(CommandHandler("todaybackupstatus", partial(today_backup_status, BACKUP_PATH_FILE=BACKUP_PATH_FILE, SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED, TIMEZONE=TIMEZONE, logger=logger)))
    application.add_handler(CommandHandler("history", partial(backup_history, BACKUP_PATH_FILE=BACKUP_PATH_FILE, logger=logger)))
    application.add_handler(CommandHandler("mbackupstatus", partial(mbackup_status, BACKUP_PATH_FILE=BACKUP_PATH_FILE, SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED, logger=logger)))
    application.add_handler(CommandHandler("mtodaybackupstatus", partial(mtoday_backup_status, BACKUP_PATH_FILE=BACKUP_PATH_FILE, SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED, logger=logger)))

    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(CommandHandler("config", config_status))
    application.add_handler(CommandHandler("getgroupid", get_group_chat_id))
    application.add_handler(CommandHandler("reloadconfig", reload_config_command))

    # Вывод оповещения вручную (вызов кода, который дублирует команду на оповещение через scheduler)
    application.add_handler(CommandHandler("notify", partial(notify_backup_command, BACKUP_PATH_FILE=BACKUP_PATH_FILE, SERVER_LIST_ALLOWED=SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED=SERVER_LIST_DISALLOWED, logger=logger)))
    application.add_error_handler(error_handler)

    # Инициализация приложения
    await application.initialize()

    # Хранение смещения для регулярных update от Telegram API
    offset = 0

    async def get_updates():
        nonlocal offset
        while True:
            try:
                updates = await application.bot.get_updates(offset=offset, timeout=20, limit=100, allowed_updates=["message", "edited_channel_post", "callback_query"])
                if updates:
                    for update in updates:
                        offset = update.update_id + 1
                        await application.process_update(update)
            except NetworkError as e:
                logger.error(f"Произошла ошибка сети: {e}")
                time.sleep(5)
            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                time.sleep(5)

    await get_updates()

if __name__ == '__main__':
    asyncio.run(main())