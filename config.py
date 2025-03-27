
import sqlite3
from threading import Lock

class Roles:
    id_project: int
    id_user: int
    id_role: int

class User:
    user_id: int = None
    tg_id: str  
    user_name: str  
    user_group: str

class Project:
    project_leader_id: str
    project_id: int = None
    project_name: str
    project_description: str
    project_need_members: int
    # project_need_members_type: list[str]
    project_members: list[User]
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
                    tg_id TEXT NOT NULL, 
                    users_name TEXT NOT NULL, 
                    users_group TEXT NOT NULL, 
                    tg_chat_id TEXT NOT NULL
                    )
                    ''')
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_leader_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL, 
                    project_description TEXT NOT NULL, 
                    project_need_members INTEGER,  
                    project_members TEXT, 
                    project_contacts TEXT NOT NULL,
                    project_id_message INTEGER,
                    project_sent BOOLEAN DEFAULT FALSE,
                    project_agreed BOOLEAN DEFAULT FALSE
                    )
                    ''')
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jokes (
                    ID INTEGER UNIQUE,
                    Joke TEXT,
                    PRIMARY KEY("ID" AUTOINCREMENT)
                    )

                    ''')
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS roles (
                    id_project INTEGER,
                    id_user INTEGER,
                    id_role INTEGER,
                    PRIMARY KEY("id_project")
                    )

                    ''')
        connection.commit()
        cursor.close()
        connection.close()

# Токен бота и ID чата публикации лежат в local_settings.py (не хранится в репозитории)
from local_settings import token, PUBLICATION_CHAT_ID

articles = [
    "1. Белоконь С.А., Золотухин Ю.Н., Мальцев А.С. и др. 'Управление квадрокоптером на основе организации движения по желаемой траектории' // Автометрия, 2012",
    
    "2. Каляев И.А., Гайдук А.Р., Капустян С.Г. 'Модели и алгоритмы коллективного управления в группах роботов' // Физматлит, 2009",
    
    "3. Amelin K., Granichin O. 'Randomized Control Strategies under Arbitrary External Noise' // IEEE Transactions on Automatic Control, 2016",
    
    "4. Kushleyev A., Mellinger D., Kumar V. 'Towards A Swarm of Agile Micro Quadrotors' // Autonomous Robots, 2013",
    
    "5. Vasarhelyi G., Viragh C., Somorjai G., et al. 'Optimized flocking of autonomous drones in confined environments' // Science Robotics, 2018",
    
    "6. Preiss J.A., Honig W., Sukhatme G.S., Ayanian N. 'Crazyswarm: A large nano-quadcopter swarm' // IEEE ICRA, 2017"
]

# def db_table_val(tg_id: str, user_name: str, user_group: str):
#     with db_lock:
#         conn = config.get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute('INSERT INTO test (tg_id, user_name, user_group) VALUES (?, ?, ?)', (tg_id, user_name, user_group))
#         conn.commit()
#         cursor.close()
#         conn.close()
