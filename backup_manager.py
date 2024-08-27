import os
import re
from datetime import datetime, timedelta

TIMEZONE = 'МСК'

# Функция для чтения пути к резервным копиям
def read_backup_path(BACKUP_PATH_FILE, logger):
    try:
        if os.path.exists(BACKUP_PATH_FILE):
            return BACKUP_PATH_FILE
        else:
            logger.error(f"Путь {BACKUP_PATH_FILE} не существует.")
            return None
    except PermissionError:
        logger.error(f"Нет доступа к пути {BACKUP_PATH_FILE}. Проверьте права доступа.")
        return None

# Функция для парсинга имени файла бэкапа
# Обновление шаблона от 24.06.2024 "SERVER-DATABASE_dd-mm-yyyy_hh_nn_ss.zip"
def parse_backup_filename(filename):
    pattern = r'^(?P<servername>[^-]+)-(?P<dbname>[^-]+)_(?P<date>\d{2}-\d{2}-\d{4})_(?P<time>\d{2}_\d{2}_\d{2})\.zip$' # SERVER-DATABASE_dd-mm-yyyy_hh_nn_ss
    match = re.match(pattern, filename)
    if match:
        return {
            'servername': match.group('servername'),
            'dbname': match.group('dbname'),
            'date': match.group('date'),
            'time': match.group('time'),
        }
    return None

# Функция для получения информации о последних бэкапах
def get_latest_backups(backup_root_path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED):
    backup_info = {}

    # Обрабатываем каждый сервер в корневой папке бэкапов
    for servername in os.listdir(backup_root_path):
        # Пропускаем сервера, которые не разрешены или запрещены для мониторинга
        if servername in SERVER_LIST_DISALLOWED or (SERVER_LIST_ALLOWED and servername not in SERVER_LIST_ALLOWED):
            continue

        server_path = os.path.join(backup_root_path, servername)
        if os.path.isdir(server_path):
            found_backup = False  # Флаг для отслеживания наличия бэкапов для текущего сервера

            # Проходим по всем файлам в директории сервера
            for root, dirs, files in os.walk(server_path):
                for backup in files:
                    backup_path = os.path.join(root, backup)
                    info = parse_backup_filename(backup)
                    if info:
                        key = (servername, info['dbname'])
                        file_mtime = os.path.getmtime(backup_path)
                        backup_datetime = datetime.fromtimestamp(file_mtime)
                        if key not in backup_info or backup_datetime > backup_info[key]['datetime']:
                            backup_info[key] = {
                                'filename': backup,
                                'datetime': backup_datetime,
                                'date': info['date'],
                            }
                        found_backup = True  # Устанавливаем флаг, если нашли хотя бы один бэкап

            # Если для текущего сервера не было найдено ни одного бэкапа
            if not found_backup:
                backup_info[(servername, None)] = {
                    'filename': None,
                    'datetime': None,
                    'date': None,
                }

    # Добавляем информацию для серверов из SERVER_LIST_ALLOWED, для которых не найдено ни одного бэкапа
    for servername in SERVER_LIST_ALLOWED:
        if not any(key[0] == servername for key in backup_info.keys()):
            backup_info[(servername, None)] = {
                'filename': None,
                'datetime': None,
                'date': None,
            }

    return backup_info


# Функция для получения информации о бэкапах за сегодня
def get_today_backups(backup_root_path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED):
    today = datetime.now().strftime('%d-%m-%Y')
    backup_info = {}

    for servername in os.listdir(backup_root_path):
        if servername in SERVER_LIST_DISALLOWED or (SERVER_LIST_ALLOWED and servername not in SERVER_LIST_ALLOWED):
            continue
        server_path = os.path.join(backup_root_path, servername)
        if os.path.isdir(server_path):
            for root, dirs, files in os.walk(server_path):
                for backup in files:
                    backup_path = os.path.join(root, backup)
                    info = parse_backup_filename(backup)
                    if info and info['date'] == today:
                        key = (servername, info['dbname'])
                        file_mtime = os.path.getmtime(backup_path)
                        backup_datetime = datetime.fromtimestamp(file_mtime)
                        if key not in backup_info or backup_datetime > backup_info[key]['datetime']:
                            backup_info[key] = {
                                'filename': backup,
                                'datetime': backup_datetime,
                                'date': info['date'],
                            }

    return backup_info

# Функция для получения истории резервных копий
def get_backup_history(backup_root_path, servername):
    history = []
    server_path = os.path.join(backup_root_path, servername)
    if os.path.isdir(server_path):
        for root, dirs, files in os.walk(server_path):
            for backup in files:
                backup_path = os.path.join(root, backup)
                file_mtime = os.path.getmtime(backup_path)
                backup_datetime = datetime.fromtimestamp(file_mtime)
                parsed_filename = parse_backup_filename(backup)
                if parsed_filename:
                    dbname = parsed_filename['dbname']
                    history.append((backup, dbname, backup_datetime))
    history.sort(key=lambda x: x[2], reverse=True)
    return history

# Функция для форматирования статуса бэкапа
def format_backup_status(servername, dbname, datetime, timezone):
    if datetime is not None:
        date_str = datetime.strftime('%d.%m.%Y %H:%M:%S')
    else:
        date_str = "НЕТ"
    return f"{servername:<15} | БД: {dbname if dbname else 'Неизвестно':<20} | {date_str}"


# Функция для форматирования статуса бэкапа (мобильная версия)
def format_backup_status_mobile(servername, dbname, datetime):
    if datetime is not None:
        date_str = datetime.strftime('%d.%m.%Y')
    else:
        date_str = "НЕТ"
    return f"{servername[:10]:<10}|{dbname if dbname else 'Неизвестно'[:10]:<10}|{date_str}"

# Функция для обработки резервных копий и генерации сообщения
def generate_backup_message(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger):
    now = datetime.now()
    start_time = datetime.combine(now.date(), datetime.min.time()).replace(hour=15) - timedelta(days=1)

    def is_recent_backup(backup_datetime):
         return backup_datetime is not None and start_time <= backup_datetime <= now

    today_backups = get_latest_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)
    recent_backups = {key: info for key, info in today_backups.items() if is_recent_backup(info['datetime'])}

    all_backups_present = True
    message = '```\n'
    for (servername, dbname), info in today_backups.items():
        if (servername, dbname) in recent_backups:
            recent_info = recent_backups[(servername, dbname)]
            message += f"{servername:<15} | БД: {dbname:<20} | {recent_info['datetime'].strftime('%d.%m.%Y %H:%M:%S')}\n"
        else:
            message += f"{servername:<15} | БД: {dbname if dbname else 'Неизвестно':<20} | НЕТ\n"
            all_backups_present = False
    message += '```'

    if all_backups_present:
        message = '✅📂🔒 Резервное копирование успешно. Работа системы продолжается без сбоев.\n' + message
    else:
        message = '❌📂⚠️ Выявлены ошибки при выполнении резервного копирования.\n' + message
    
    # Экранирование символов для MarkdownV2
    message = message.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('-', '\\-').replace('|', '\\|').replace('.', '\\.')
    
    return message

# Асинхронная функция для обработки команды /notify
async def notify_backup_command(update, context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)

    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    message = generate_backup_message(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger)
    await update.message.reply_text(message, parse_mode='MarkdownV2')

# Асинхронная функция для уведомлений по расписанию
async def notify_backup_status(context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, CHAT_ID, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)

    if not path:
        await context['application'].bot.send_message(CHAT_ID, 'Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    message = generate_backup_message(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger)
    await context['application'].bot.send_message(CHAT_ID, message, parse_mode='MarkdownV2')


# Асинхронная функция для проверки бэкапов за сегодня (мобильная версия)
async def mtoday_backup_status(update, context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)
    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    today_backups = get_today_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)
    all_backups = get_latest_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)
    today_date = datetime.now().strftime('%d.%m.%Y')

    message = 'Статус резервных копий на сегодня:\n```\n'
    for (servername, dbname), info in all_backups.items():
        if (servername, dbname) in today_backups:
            today_info = today_backups[(servername, dbname)]
            message += format_backup_status_mobile(servername, dbname, today_info['datetime']) + '\n'
        else:
            message += f"{servername[:10]:<10}|{dbname if dbname else 'Неизвестно'[:10]:<10}|НЕТ\n"
    message += '```'

    await update.message.reply_text(message, parse_mode='Markdown')

# Асинхронная функция для проверки статуса бэкапов (мобильная версия)
async def mbackup_status(update, context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)
    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    backups = get_latest_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)

    if backups:
        message = 'Статус текущих резервных копий:\n```\n'
        for (servername, dbname), info in backups.items():
            message += format_backup_status_mobile(servername, dbname, info['datetime']) + '\n'
        message += '```'
    else:
        message = 'Бэкапы не найдены.'

    await update.message.reply_text(message, parse_mode='Markdown')

# Асинхронная функция для получения истории резервных копий
async def backup_history(update, context, BACKUP_PATH_FILE, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)
    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    if len(context.args) == 0:
        await update.message.reply_text('Использование: /history <servername>')
        return

    servername = context.args[0]
    history = get_backup_history(path, servername)

    if history:
        message = f"История резервных копий для сервера {servername}:\n```\n"
        for backup, dbname, datetime in history:
            message += format_backup_status(servername, dbname, datetime, TIMEZONE) + '\n'
        message += '```'
    else:
        message = f"Нет данных о резервных копиях для сервера {servername}."

    await update.message.reply_text(message, parse_mode='Markdown')

# Асинхронная функция для проверки бэкапов за сегодня
async def today_backup_status(update, context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, TIMEZONE, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)
    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    today_backups = get_today_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)
    all_backups = get_latest_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)
    today_date = datetime.now().strftime('%d.%m.%Y')

    message = 'Статус резервных копий на сегодня:\n```\n'
    for (servername, dbname), info in all_backups.items():
        if (servername, dbname) in today_backups:
            today_info = today_backups[(servername, dbname)]
            message += format_backup_status(servername, dbname, today_info['datetime'], TIMEZONE) + '\n'
        else:
            message += f"{servername:<15} | БД: {dbname if dbname else 'Неизвестно':<20} | КОПИЯ ОТСУТСТВУЕТ\n"
    message += '```'

    await update.message.reply_text(message, parse_mode='Markdown')

# Асинхронная функция для проверки статуса бэкапов
async def backup_status(update, context, BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, TIMEZONE, logger):
    path = read_backup_path(BACKUP_PATH_FILE, logger)
    if not path:
        await update.message.reply_text('Путь к бэкапам не установлен. Используйте команду /pathbackup для установки пути.')
        return

    backups = get_latest_backups(path, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED)

    if backups:
        message = 'Статус текущих резервных копий:\n```\n'
        for (servername, dbname), info in backups.items():
            message += format_backup_status(servername, dbname, info['datetime'], TIMEZONE) + '\n'
        message += '```'
    else:
        message = 'Бэкапы не найдены.'

    await update.message.reply_text(message, parse_mode='Markdown')

