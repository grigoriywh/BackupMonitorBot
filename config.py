import configparser

# Функция для чтения и отображения конфигурационных данных
def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def write_backup_path(path):
    config = read_config()
    config['Paths']['BACKUP_PATH_FILE'] = path
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def write_chat_id(chat_id):
    config = read_config()
    config['Notification']['CHAT_ID'] = str(chat_id)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

# Функция для чтения и отображения конфигурационных данных
def get_config_values():
    config = read_config()
    backup_path_file = config['Paths']['BACKUP_PATH_FILE']
    server_list_allowed = config['Servers']['SERVER_LIST_ALLOWED'].split(', ')
    server_list_disallowed = config['Servers']['SERVER_LIST_DISALLOWED'].split(', ')
    chat_id = config['Notification']['CHAT_ID']
    time_notification = config['Notification']['TIME_NOTIFICATION']
    return backup_path_file, server_list_allowed, server_list_disallowed, chat_id, time_notification

# experimental
def reload_config():
    global BACKUP_PATH_FILE, SERVER_LIST_ALLOWED, SERVER_LIST_DISALLOWED, TIME_NOTIFICATION, CHAT_ID
    config = read_config()
    BACKUP_PATH_FILE = config['Paths']['BACKUP_PATH_FILE']
    SERVER_LIST_ALLOWED = config['Servers']['SERVER_LIST_ALLOWED'].split(', ')
    SERVER_LIST_DISALLOWED = config['Servers']['SERVER_LIST_DISALLOWED'].split(', ')
    TIME_NOTIFICATION = config['Notification']['TIME_NOTIFICATION']
    CHAT_ID = config.get('Notification', 'CHAT_ID', fallback=None)
