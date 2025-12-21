import sqlite3
from threading import Lock

# Токен бота и ID чатов лежат в local_settings.py (не хранится в репозитории).
# Шаблон: local_settings.example.py
from local_settings import (token, REVIEWER_CHAT_IDS, REVIEWER_USERNAME,
                            PUBLICATION_CHAT_ID, PUBLICATION_THREAD_ID)

class Roles:
    id_project: int
    id_user: int
    id_role: int

class User:
    user_id: int = None
    tg_id: str  
    user_name: str  
    user_group: str
    tg_chat_id: str

class Project:
    project_leader_id: str
    project_id: int = None
    project_name: str
    project_description: str
    project_need_members: int
    # project_need_members_type: list[str]
    #project_members: list[User]
    project_contacts: str
    project_sent: False
    project_id_message: int
    project_agreed: False

db_lock = Lock()
def get_db_connection():
    return sqlite3.connect('dbusers.db')

def check_database_state():
    with db_lock:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id TEXT,
                    users_name TEXT NOT NULL,
                    users_group TEXT,
                    tg_chat_id TEXT NOT NULL,
                    birth_date TEXT DEFAULT '',
                    institute TEXT DEFAULT '',
                    phone_number TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    social_link TEXT DEFAULT '',
                    menu_session TEXT DEFAULT ''
                    )
                    ''')
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jokes (
                    ID INTEGER UNIQUE,
                    Joke TEXT,
                    PRIMARY KEY("ID" AUTOINCREMENT)
                    )

                    ''')
        # cursor.execute('''
        #             CREATE TABLE IF NOT EXISTS roles (
        #             id_project INTEGER,
        #             id_user INTEGER,
        #             id_role INTEGER,
        #             PRIMARY KEY("id_project')
        #             )

        #             ''')
        connection.commit()
        cursor.close()
        connection.close()

# def db_table_val(tg_id: str, user_name: str, user_group: str):
#     with db_lock:
#         conn = config.get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute('INSERT INTO test (tg_id, user_name, user_group) VALUES (?, ?, ?)', (tg_id, user_name, user_group))
#         conn.commit()
#         cursor.close()
#         conn.close()
