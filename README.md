# BackupMonitorBot

BackupMonitorBot - это бот для Telegram, разработанный для мониторинга резервных копий и отправки уведомлений о статусе резервных копий.

## Функциональность

- Отправка уведомлений о статусе резервных копий.
- Получение статуса текущих резервных копий.
- Получение статуса резервных копий за сегодняшний день.
- Получение истории резервных копий для конкретного сервера.
- Управление конфигурацией бота.

## Установка

1. Клонируйте репозиторий на ваш локальный компьютер:
    ```sh
    git clone https://github.com/yourusername/BackupMonitorBot.git
    ```
2. Перейдите в директорию проекта:
    ```sh
    cd BackupMonitorBot
    ```
3. Установите необходимые зависимости:
    ```sh
    pip install -r requirements.txt
    ```

## Настройка

1. Создайте файл `config.ini` в корневой директории проекта и добавьте следующие настройки:

    ```ini
    [Paths]
    BACKUP_PATH_FILE = /path/to/backup/files

    [Servers]
    SERVER_LIST_ALLOWED = server1, server2
    SERVER_LIST_DISALLOWED = server3, server4

    [Notification]
    CHAT_ID = your_chat_id
    TIME_NOTIFICATION = 07:00:00
    ```

2. Обновите переменную `TOKEN` в файле `BackupMonitorBot.py` вашим токеном, полученным от BotFather.

## Использование

## Доступные команды
/start - Начать работу с ботом
/backupstatus - Статус всех резервных копий
/todaybackupstatus - Резервные копии за сегодня
/history <сервер> - История резервных копий сервера
/mbackupstatus - Статус резервных копий (моб. версия)
/mtodaybackupstatus - Резервные копии за сегодня (моб. версия)
/config - Показать настройки конфигурации
/getgroupid - Получить и сохранить ID группы
/reloadconfig - Обновить информацию из файла config.ini
/notify - Отправить уведомление о статусе резервных копий

## Лицензия
Этот проект лицензирован под лицензией MIT. Подробности см. в файле LICENSE.