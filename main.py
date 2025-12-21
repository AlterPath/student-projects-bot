import config
import telebot
from telebot import types
from threading import Lock
import time
import threading

# Метка текущей сессии (перезапуск бота)
CURRENT_SESSION = str(int(time.time()))

#TODO
#Отлов при выключении бота
#Добавление компетенций 
#при регистрации высылка в анкету 

#Отлов проектов с названиями кнопок

"""
Фильтрация проектов
Пересылка другому боту, где уже человек проверяет проект на нормальность.
Отправка отзыва о проекте которые не прошли фильтрацию.
Создание отдельного раздела с отправленными на верификацию проектами.

"""

# Создаем блокировку для потокобезопасного доступа к БД
db_lock = Lock()


# Глобальная переменная для хранения названия проекта
current_project_name = None

bot = telebot.TeleBot(config.token)
config.check_database_state()

def init_db_pragmas():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute('PRAGMA journal_mode = WAL')
                    cursor.execute('PRAGMA foreign_keys = ON')
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.3)

init_db_pragmas()

def ensure_projects_competencies_column():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute("PRAGMA table_info(projects)")
                    cols = [row[1] for row in cursor.fetchall()]
                    if 'project_competencies' not in cols:
                        cursor.execute('ALTER TABLE projects ADD COLUMN project_competencies TEXT DEFAULT ""')
                        conn.commit()
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.3)

ensure_projects_competencies_column()

def ensure_review_columns():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute("PRAGMA table_info(projects)")
                    cols = [row[1] for row in cursor.fetchall()]
                    additions = []
                    if 'review_approved' not in cols:
                        additions.append('ADD COLUMN review_approved INTEGER DEFAULT 0')
                    if 'review_comment' not in cols:
                        additions.append("ADD COLUMN review_comment TEXT DEFAULT ''")
                    if 'review_reviewer_chat_id' not in cols:
                        additions.append("ADD COLUMN review_reviewer_chat_id TEXT DEFAULT ''")
                    if 'last_review_request' not in cols:
                        additions.append("ADD COLUMN last_review_request INTEGER DEFAULT 0")
                    for alter in additions:
                        cursor.execute(f'ALTER TABLE projects {alter}')
                    if additions:
                        conn.commit()
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.3)

ensure_review_columns()


def ensure_users_menu_session_column():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute("PRAGMA table_info(users)")
                    cols = [row[1] for row in cursor.fetchall()]
                    if 'menu_session' not in cols:
                        cursor.execute("ALTER TABLE users ADD COLUMN menu_session TEXT DEFAULT ''")
                        conn.commit()
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.2)

ensure_users_menu_session_column()

def ensure_users_profile_columns():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute("PRAGMA table_info(users)")
                    cols = [row[1] for row in cursor.fetchall()]
                    additions = []
                    if 'birth_date' not in cols:
                        additions.append("ADD COLUMN birth_date TEXT DEFAULT ''")
                    if 'institute' not in cols:
                        additions.append("ADD COLUMN institute TEXT DEFAULT ''")
                    if 'phone_number' not in cols:
                        additions.append("ADD COLUMN phone_number TEXT DEFAULT ''")
                    if 'email' not in cols:
                        additions.append("ADD COLUMN email TEXT DEFAULT ''")
                    if 'social_link' not in cols:
                        additions.append("ADD COLUMN social_link TEXT DEFAULT ''")
                    for alter in additions:
                        cursor.execute(f'ALTER TABLE users {alter}')
                    if additions:
                        conn.commit()
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.2)

ensure_users_profile_columns()

def ensure_possible_projects_table():
    attempts_left = 5
    while attempts_left > 0:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS possible_projects (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tg_chat_id TEXT NOT NULL,
                            title TEXT DEFAULT '',
                            idea TEXT DEFAULT '',
                            short_desc TEXT DEFAULT '',
                            direction TEXT DEFAULT '',
                            source TEXT DEFAULT '',
                            created_at INTEGER DEFAULT (strftime('%s','now'))
                        )
                    ''')
                    conn.commit()
                    return
                finally:
                    cursor.close()
                    conn.close()
        except Exception:
            attempts_left -= 1
            time.sleep(0.2)

ensure_possible_projects_table()


def get_latest_possible_field(tg_chat_id, field_name):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute(f"SELECT {field_name} FROM possible_projects WHERE tg_chat_id = ? ORDER BY id DESC LIMIT 1", (str(tg_chat_id),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        if not row:
            return ''
        return row[0] or ''
    except Exception:
        return ''

def get_latest_possible_id(tg_chat_id):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute("SELECT id FROM possible_projects WHERE tg_chat_id = ? ORDER BY id DESC LIMIT 1", (str(tg_chat_id),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        if not row:
            return None
        return row[0]
    except Exception:
        return None

def refresh_menu_if_needed(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('SELECT menu_session FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
            row = cursor.fetchone()
            need_refresh = True
            if row is not None and row[0] == CURRENT_SESSION:
                need_refresh = False
            if need_refresh:
                cursor.execute('UPDATE users SET menu_session = ? WHERE tg_chat_id = ?', (CURRENT_SESSION, str(message.from_user.id)))
                conn.commit()
            cursor.close()
            conn.close()
        if need_refresh:
            show_main_menu(message)
            return True
    except Exception:
        pass
    return False


_rr_index = 0

def get_next_reviewer_chat_id():
    global _rr_index
    reviewer_ids = getattr(config, 'REVIEWER_CHAT_IDS', None)
    if reviewer_ids and isinstance(reviewer_ids, (list, tuple)):
        normalized = [str(x).strip() for x in reviewer_ids if str(x).strip()]
    else:
        normalized = []
    if not normalized:
        single = getattr(config, 'REVIEWER_CHAT_ID', '') or ''
        return str(single).strip()

    if _rr_index < 0 or _rr_index >= len(normalized):
        _rr_index = 0
    chosen = normalized[_rr_index]
    _rr_index = (_rr_index + 1) % len(normalized)
    return chosen

def ensure_user_chat_record(chat_id):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('SELECT user_id FROM users WHERE tg_chat_id = ?', (str(chat_id),))
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    'INSERT INTO users (users_name, users_group, tg_chat_id, tg_id) VALUES (?, ?, ?, ?)',
                    ("", "", str(chat_id), "")
                )
                conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass


def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Заполнить анкету")
    btn5 = types.KeyboardButton("Личные данные")
    btn2 = types.KeyboardButton("Добавить возможный проект")
    btn3 = types.KeyboardButton("Список проектов")
    btn4 = types.KeyboardButton("Q&A")
    markup.row(btn1, btn5)
    markup.row(btn3, btn2)
    markup.row(btn4)
    bot.send_message(message.from_user.id, "Вы в главном меню", reply_markup=markup)

def start_possible_project_flow(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('INSERT INTO possible_projects (tg_chat_id) VALUES (?)', (str(message.from_user.id),))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    msg = bot.send_message(message.from_user.id, "Введите Название:")
    bot.register_next_step_handler(msg, handle_possible_title)

def handle_possible_title(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            last_id = get_latest_possible_id(message.from_user.id)
            if last_id is not None:
                cursor.execute('UPDATE possible_projects SET title = ? WHERE id = ?', (message.text or '', last_id))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    msg = bot.send_message(message.from_user.id, "Опишите идею:")
    bot.register_next_step_handler(msg, handle_possible_idea)

def handle_possible_idea(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            last_id = get_latest_possible_id(message.from_user.id)
            if last_id is not None:
                cursor.execute('UPDATE possible_projects SET idea = ? WHERE id = ?', (message.text or '', last_id))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    msg = bot.send_message(message.from_user.id, "Краткое описание:")
    bot.register_next_step_handler(msg, handle_possible_short_desc)

def handle_possible_short_desc(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            last_id = get_latest_possible_id(message.from_user.id)
            if last_id is not None:
                cursor.execute('UPDATE possible_projects SET short_desc = ? WHERE id = ?', (message.text or '', last_id))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    msg = bot.send_message(message.from_user.id, "Направление:")
    bot.register_next_step_handler(msg, handle_possible_direction)

def handle_possible_direction(message):
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            last_id = get_latest_possible_id(message.from_user.id)
            if last_id is not None:
                cursor.execute('UPDATE possible_projects SET direction = ? WHERE id = ?', (message.text or '', last_id))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    msg = bot.send_message(message.from_user.id, "Источник (если есть):")
    bot.register_next_step_handler(msg, handle_possible_source)

def handle_possible_source(message):
    chat_id = message.from_user.id
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            last_id = get_latest_possible_id(chat_id)
            if last_id is not None:
                cursor.execute('UPDATE possible_projects SET source = ? WHERE id = ?', (message.text or '', last_id))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass

    # Достаём данные пользователя
    users_name = ''
    users_group = ''
    social_link = ''
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('''
                SELECT users_name, users_group, social_link
                FROM users WHERE tg_chat_id = ?
            ''', (str(chat_id),))
            row = cursor.fetchone()
            if row:
                users_name, users_group, social_link = row
            cursor.close()
            conn.close()
    except Exception:
        pass

    reviewer_chat_id = get_next_reviewer_chat_id()
    if not reviewer_chat_id:
        bot.send_message(chat_id, "REVIEWER_CHAT_ID не задан в конфиге.")
        return

    message_text = (
        "💡 Возможный проект\n\n"
        f"Отправитель: {users_name or ''}\n"
        f"Группа: {users_group or ''}\n"
        f"Telegram ID: {chat_id}\n"
        f"Telegram ссылка: {social_link or ''}\n\n"
        f"Название: {get_latest_possible_field(chat_id, 'title')}\n"
        f"Идея: {get_latest_possible_field(chat_id, 'idea')}\n"
        f"Краткое описание: {get_latest_possible_field(chat_id, 'short_desc')}\n"
        f"Направление: {get_latest_possible_field(chat_id, 'direction')}\n"
        f"Источник: {get_latest_possible_field(chat_id, 'source')}\n"
    )

    try:
        bot.send_message(reviewer_chat_id, message_text)
        bot.send_message(chat_id, "Отправлено проверяющему.")
    except Exception as e:
        bot.send_message(chat_id, f"Не удалось отправить: {e}")

    show_main_menu(message)

def norm_text(message):
    return (message.text or "").strip().lower()

def q_and_a(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btnQA1 = types.KeyboardButton("Раз вопрос")
    btnQA2 = types.KeyboardButton("Два вопрос")
    btnQA3 = types.KeyboardButton("Три вопрос")
    btn_back = types.KeyboardButton("Назад в меню")
    markup.row(btnQA1)
    markup.row(btnQA2)
    markup.row(btnQA3)
    markup.row(btn_back)
    msg = bot.send_message(message.from_user.id, "Выберите вопрос или нажмите 'Назад в меню' для возврата в меню", reply_markup=markup)
    
    bot.register_next_step_handler(msg, q_and_a_handle_choice)

def q_and_a_handle_choice(message):
    txt = norm_text(message)
    if txt == "раз вопрос":
        bot.send_message(message.from_user.id, "1")
        q_and_a(message)
    elif txt == "два вопрос":
        bot.send_message(message.from_user.id, "2")
        q_and_a(message)
    elif txt == "три вопрос":
        bot.send_message(message.from_user.id, "3")
        q_and_a(message)
    elif txt == "назад в меню":
        show_main_menu(message)

def q_and_a_edit_handler(message, user_id):
    txt = norm_text(message)
    if txt == "раз вопрос":
        msg = bot.send_message(message.from_user.id, "1")
        bot.register_next_step_handler(msg, q_and_a)
    elif txt == "два вопрос":
        msg = bot.send_message(message.from_user.id, "2")
        bot.register_next_step_handler(msg, q_and_a)
    elif txt == "три вопрос":
        msg = bot.send_message(message.from_user.id, "3")
        bot.register_next_step_handler(msg, q_and_a)
    else:
        show_project_actions(message, user_id)

def show_project_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton("Добавить проект")
    btn_chs = types.KeyboardButton("Выбрать проект")
    btn_back = types.KeyboardButton("Назад в меню")
    markup.row(btn_add)
    markup.row(btn_chs)
    markup.row(btn_back)
    bot.send_message(message.from_user.id, "Введите 'Добавить проект', 'Выбрать проект' или нажмите 'Назад в меню' для возврата в меню", reply_markup=markup)

def process_registration_step(message, step=1):
    if step == 1:  
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (users_name, users_group, tg_chat_id) VALUES (?, ?, ?)', 
                        (message.text, "", str(message.chat.id)))
            conn.commit()
            cursor.close()
            conn.close()
        
        msg = bot.send_message(message.from_user.id, "Приятно познакомиться :) Из какой ты группы? Если вы преподаватель, напишите: Я преподаватель.")
        bot.register_next_step_handler(msg, process_registration_step, 2)
        
    elif step == 2: 
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET users_group = ? WHERE tg_chat_id = ?',
                          (message.text, str(message.from_user.id)))
            conn.commit()
            cursor.close()
            conn.close()
        
        msg = bot.send_message(message.from_user.id, "Отлично! Теперь введите ваш Telegram или любой другой контакт:")
        bot.register_next_step_handler(msg, process_registration_step, 3)
        
    elif step == 3:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET tg_id = ? WHERE tg_chat_id = ?',
                        (message.text, str(message.from_user.id)))
            conn.commit()
            cursor.close()
            conn.close()
        bot.register_next_step_handler(message, process_registration_step, 4)

    elif step == 4:  
        bot.send_message(message.from_user.id, "Регистрация завершена.")

def process_project_name(message):
    project_name = message.text
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT project_id FROM projects WHERE project_name = ?', (project_name,))
        existing_project = cursor.fetchone()
        cursor.close()
        conn.close()
        
    if existing_project:
        msg = bot.send_message(message.from_user.id, "Проект с таким названием уже существует. Пожалуйста, выберите другое название:")
        bot.register_next_step_handler(msg, process_project_name)
        return
    msg = bot.send_message(message.from_user.id, "Введите описание проекта:")
    bot.register_next_step_handler(msg, process_project_description, project_name)

def process_project_description(message, project_name):
    project_description = message.text
    msg = bot.send_message(message.from_user.id, "Введите требуемые компетенции (через запятую):")
    bot.register_next_step_handler(msg, process_project_competencies, project_name, project_description)

def process_project_competencies(message, project_name, project_description):
    project_competencies = message.text
    msg = bot.send_message(message.from_user.id, "Введите количество участников: ")
    bot.register_next_step_handler(msg, process_project_members, project_name, project_description, project_competencies)

def process_project_members(message, project_name, project_description, project_competencies):
    try:
        project_need_members = int(message.text)
        msg = bot.send_message(message.from_user.id, "Введите контактные данные:")
        bot.register_next_step_handler(msg, save_project, project_name, project_description, project_competencies, project_need_members)
    except ValueError:
        msg = bot.send_message(message.from_user.id, "Пожалуйста, введите число!")
        bot.register_next_step_handler(msg, process_project_members, project_name, project_description, project_competencies)

def save_project(message, project_name, project_description, project_competencies, project_need_members):
    project_contacts = message.text
    
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
        user_id = cursor.fetchone()[0]
        
        cursor.execute('''INSERT INTO projects 
                         (project_leader_id, project_name, project_description, project_contacts, project_need_members, project_competencies)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user_id, project_name, project_description, project_contacts, project_need_members, project_competencies))
        project_id = cursor.execute('SELECT project_id FROM projects WHERE project_leader_id = ? AND project_name = ?', (user_id, project_name)).fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
    
    bot.send_message(message.from_user.id, "Проект успешно добавлен!")
    agreement_on_sending(message, project_id)

def deleting_project(message, project_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_yes = types.KeyboardButton("Да")
    btn_no = types.KeyboardButton("Нет") 
    markup.add(btn_yes, btn_no)
    
    msg = bot.send_message(message.from_user.id, "Хотите ли вы удалить свой проект?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_delete_confirmation, project_id)

def process_delete_confirmation(message, project_id):
    if norm_text(message) == "да":
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()

                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute(
                    'SELECT user_id FROM users WHERE tg_chat_id = ?',
                    (str(message.from_user.id),)
                )
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    conn.close()
                    bot.send_message(message.from_user.id, "Вы не зарегистрированы.")
                    return

                user_id = row[0]

                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute(
                    'DELETE FROM projects WHERE project_id = ? AND project_leader_id = ?',
                    (project_id, user_id)
                )
                deleted = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()

            if deleted and deleted > 0:
                bot.send_message(message.from_user.id, "Ваш проект удален.")
            else:
                bot.send_message(message.from_user.id, "Проект не найден или не принадлежит вам.")
        except Exception as e:
            bot.send_message(message.from_user.id, f"Ошибка при удалении: {e}")
    else:
        bot.send_message(message.from_user.id, "Хорошо, проект не будет удален.")
    
    show_project_menu(message)

def agreement_on_sending(message, project_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_yes = types.KeyboardButton("Да")
    btn_no = types.KeyboardButton("Нет") 
    markup.add(btn_yes, btn_no)
    
    msg = bot.send_message(message.from_user.id, "Хотите ли вы отправить свой проект на проверку?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_agreement_response, project_id)

def process_agreement_response(message, project_id):
    if norm_text(message) == "да":
        send_to_fixed_reviewer(message, project_id)
    else:
        bot.send_message(message.from_user.id, "Хорошо, проект не будет отправлен на проверку.")
        show_project_menu(message)


def edit_account(message, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Изменить Ф.И.О.")
    btn2 = types.KeyboardButton("Изменить дату рождения")
    btn3 = types.KeyboardButton("Изменить институт")
    btn4a = types.KeyboardButton("Изменить академическую группу")
    btn5 = types.KeyboardButton("Изменить номер телефона")
    btn6 = types.KeyboardButton("Изменить эл. почту")
    btn7 = types.KeyboardButton("Изменить соц. ссылку")
    btn4 = types.KeyboardButton("Назад в меню")
    markup.row(btn1, btn2)
    markup.row(btn3, btn4a)
    markup.row(btn5, btn6)
    markup.row(btn7)
    markup.row(btn4)
    
    msg = bot.send_message(message.from_user.id, "Выберите, что хотите изменить:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_edit_choice, user_id)

def process_edit_choice(message, user_id):
    if message.text == "Изменить Ф.И.О.":
        msg = bot.send_message(message.from_user.id, "Введите Ф.И.О. полностью:")
        bot.register_next_step_handler(msg, update_name)
    elif message.text == "Изменить дату рождения":
        msg = bot.send_message(message.from_user.id, "Введите дату рождения (например, 01.01.2000):")
        bot.register_next_step_handler(msg, update_birth_date)
    elif message.text == "Изменить институт":
        msg = bot.send_message(message.from_user.id, "Введите название института:")
        bot.register_next_step_handler(msg, update_institute)
    elif message.text == "Изменить академическую группу":
        msg = bot.send_message(message.from_user.id, "Введите академическую группу:")
        bot.register_next_step_handler(msg, update_group)
    elif message.text == "Изменить номер телефона":
        msg = bot.send_message(message.from_user.id, "Введите номер телефона:")
        bot.register_next_step_handler(msg, update_phone_number)
    elif message.text == "Изменить эл. почту":
        msg = bot.send_message(message.from_user.id, "Введите адрес электронной почты:")
        bot.register_next_step_handler(msg, update_email)
    elif message.text == "Изменить соц. ссылку":
        msg = bot.send_message(message.from_user.id, "Вставьте ссылку на вашу страницу в соцсетях:")
        bot.register_next_step_handler(msg, update_social_link)
    elif norm_text(message) == "назад в меню":
        show_main_menu(message)
    else:
        show_project_actions(message, user_id)

def update_name(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET users_name = ? WHERE tg_chat_id = ?', 
                      (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Имя успешно обновлено!")
    show_main_menu(message)

def update_group(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET users_group = ? WHERE tg_chat_id = ?',
                      (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Группа успешно обновлена!")
    show_main_menu(message)

def update_contact(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET tg_id = ? WHERE tg_chat_id = ?',
                      (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Контакт успешно обновлен!")
    show_main_menu(message)

def update_birth_date(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET birth_date = ? WHERE tg_chat_id = ?', (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Дата рождения обновлена!")
    show_main_menu(message)

def update_institute(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET institute = ? WHERE tg_chat_id = ?', (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Институт обновлён!")
    show_main_menu(message)

def update_phone_number(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET phone_number = ? WHERE tg_chat_id = ?', (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Номер телефона обновлён!")
    show_main_menu(message)

def update_email(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET email = ? WHERE tg_chat_id = ?', (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Эл. почта обновлена!")
    show_main_menu(message)

def update_social_link(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET social_link = ? WHERE tg_chat_id = ?', (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Ссылка обновлена!")
    show_main_menu(message)


def edit_project(message, project_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_name = types.KeyboardButton("Изменить название")
    btn_desc = types.KeyboardButton("Изменить описание") 
    btn_members = types.KeyboardButton("Изменить количество участников")
    btn_contacts = types.KeyboardButton("Изменить контакты")
    btn_comp = types.KeyboardButton("Изменить компетенции")
    btn_back = types.KeyboardButton("Назад")
    markup.row(btn_name, btn_desc)
    markup.row(btn_members, btn_contacts)
    markup.row(btn_comp)
    markup.row(btn_back)
    
    msg = bot.send_message(message.from_user.id, "Выберите, что хотите изменить:", reply_markup=markup)
    
    def handle_edit_choice(message):
        txt = norm_text(message)
        if txt == "изменить название":
            msg = bot.send_message(message.from_user.id, "Введите новое название проекта:")
            bot.register_next_step_handler(msg, update_project_name, project_id)
        elif txt == "изменить описание":
            msg = bot.send_message(message.from_user.id, "Введите новое описание проекта:")
            bot.register_next_step_handler(msg, update_project_description, project_id)
        elif txt == "изменить количество участников":
            msg = bot.send_message(message.from_user.id, "Введите новое количество требуемых участников:")
            bot.register_next_step_handler(msg, update_project_members, project_id)
        elif txt == "изменить контакты":
            msg = bot.send_message(message.from_user.id, "Введите новые контактные данные:")
            bot.register_next_step_handler(msg, update_project_contacts, project_id)
        elif txt == "изменить компетенции":
            msg = bot.send_message(message.from_user.id, "Введите новые компетенции (через запятую):")
            bot.register_next_step_handler(msg, update_project_competencies, project_id)
        elif txt == "назад":
            show_project_actions(message, project_id)
            
    bot.register_next_step_handler(msg, handle_edit_choice)

def update_project_name(message, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        project_name = message.text
        cursor.execute('SELECT project_id FROM projects WHERE project_name = ?', (project_name,))
        existing_project = cursor.fetchone()
        if existing_project:
            cursor.close()
            conn.close()
            msg = bot.send_message(message.from_user.id, "Проект с таким названием уже существует. Пожалуйста, выберите другое название:")
            bot.register_next_step_handler(msg, update_project_name, project_id)
            return
        cursor.execute('UPDATE projects SET project_name = ? WHERE project_id = ?', (project_name, project_id))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Название проекта успешно обновлено!")
    show_project_actions(message, project_id)

def update_project_description(message, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE projects SET project_description = ? WHERE project_id = ?',
                      (message.text, project_id))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Описание проекта успешно обновлено!")
    show_project_actions(message, project_id)

def update_project_members(message, project_id):
    try:
        members_count = int(message.text)
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE projects SET project_need_members = ? WHERE project_id = ?',
                          (members_count, project_id))
            conn.commit()
            cursor.close()
            conn.close()
        bot.send_message(message.from_user.id, "Количество требуемых участников успешно обновлено!")
    except ValueError:
        bot.send_message(message.from_user.id, "Пожалуйста, введите число!")
    show_project_actions(message, project_id)

def update_project_contacts(message, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE projects SET project_contacts = ? WHERE project_id = ?',
                      (message.text, project_id))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Контактные данные успешно обновлены!")
    show_project_actions(message, project_id)

def update_project_competencies(message, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE projects SET project_competencies = ? WHERE project_id = ?',
                      (message.text, project_id))
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(message.from_user.id, "Компетенции успешно обновлены!")
    show_project_actions(message, project_id)

@bot.message_handler(func=lambda message: norm_text(message) == "выбрать проект")
def project_choice(message):
    bot.send_message(message.from_user.id, "Напишите название проекта:")
    bot.register_next_step_handler(message, search_project_name)

def search_project_name(message):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        project_name = (message.text or "").strip()
        cursor.execute('SELECT user_id FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
        user_id_result = cursor.fetchone()
        
        if user_id_result is None:
            bot.send_message(message.from_user.id, "Пользователь не найден")
            cursor.close()
            conn.close()
            return
            
        user_id = user_id_result[0]
        cursor.execute('SELECT project_id FROM projects WHERE project_leader_id = ? AND lower(project_name) = lower(?)', (user_id, project_name))
        result = cursor.fetchone()
        
        if result is None:
            bot.send_message(message.from_user.id, "Проект не найден. Проверьте правильность названия проекта.")
            cursor.close()
            conn.close()
            return
            
        project_id = result[0]
        cursor.close()
        conn.close()
        
        show_project_actions(message, project_id)

def show_project_actions(message, project_id):
    global current_project_name
    current_project_name = project_id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_edit = types.KeyboardButton("Изменить проект")
    btn_publish = types.KeyboardButton("Опубликовать проект")
    btn_send_for_review = types.KeyboardButton("Отправить на проверку")
    btn_delete = types.KeyboardButton("Удалить проект")
    btn_back = types.KeyboardButton("Назад")
    markup.row(btn_edit, btn_publish)
    markup.row(btn_send_for_review)
    markup.row(btn_delete)
    markup.row(btn_back)
    
    def handle_project_action(message):
        txt = norm_text(message)
        if txt == "изменить проект":
            edit_project(message, project_id)
        elif txt == "опубликовать проект":
            publish_project_if_approved(message, project_id)
        elif txt == "удалить проект":
            deleting_project(message, project_id)
        elif txt == "назад":
            show_project_menu(message)
        elif txt == "отправить на проверку":
            send_to_fixed_reviewer(message, project_id)
    
    msg = bot.send_message(message.from_user.id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(msg, handle_project_action)


_pending_review_comments = {}
_pending_publication_confirmations = {}

def send_to_fixed_reviewer(message, project_id):
    reviewer_chat_id = get_next_reviewer_chat_id()
    if not reviewer_chat_id:
        bot.send_message(message.from_user.id, "REVIEWER_CHAT_ID не задан в конфиге.")
        return
    
    current_time = int(time.time())
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT last_review_request FROM projects WHERE project_id = ?', (project_id,))
        row = cursor.fetchone()
        last_request = row[0] if row and row[0] else 0
        
        if last_request > 0 and (current_time - last_request) < 86400: 
            hours_left = 24 - ((current_time - last_request) // 3600)
            bot.send_message(message.from_user.id, f"Проект можно отправить на повторную проверку только через {hours_left} часов.")
            cursor.close()
            conn.close()
            show_project_actions(message, project_id)
            return
        
        cursor.execute('UPDATE projects SET review_reviewer_chat_id = ?, last_review_request = ? WHERE project_id = ?', 
                      (str(reviewer_chat_id), current_time, project_id))
        conn.commit()
        cursor.close()
        conn.close()
    
    proceed_send_review_card(message, project_id, reviewer_chat_id)


def handle_reviewer_username_entered(message, project_id):
    return


def handle_reviewer_chat_id_entered(message, project_id, reviewer_username):
    return


def get_project_card(project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('PRAGMA busy_timeout = 5000')
        cursor.execute('''
            SELECT p.project_id, p.project_name, p.project_description, p.project_need_members, p.project_competencies, p.project_contacts, u.users_name
            FROM projects p
            JOIN users u ON p.project_leader_id = u.user_id
            WHERE p.project_id = ?
        ''', (project_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    if not row:
        return None
    project_id, name, desc, need_members, competencies, contacts, author_name = row
    text = (
        f"📝 Проект на проверку (ID: {project_id})\n\n"
        f"Название: {name}\n"
        f"Автор: {author_name}\n"
        f"Описание: {desc}\n"
        f"Требуется участников: {need_members}\n"
        f"Требуемые компетенции: {competencies}\n"
        f"Контакты: {contacts}\n"
    )
    return text


def proceed_send_review_card(message, project_id, reviewer_chat_id):
    card = get_project_card(project_id)
    if not card:
        bot.send_message(message.from_user.id, "Проект не найден.")
        return

    kb = types.InlineKeyboardMarkup()
    btn_reject = types.InlineKeyboardButton(text="Отправить обратно", callback_data=f"review:reject:{project_id}")
    btn_publish = types.InlineKeyboardButton(text="Опубликовать", callback_data=f"review:approve:{project_id}")
    kb.add(btn_reject, btn_publish)

    try:
        sent = bot.send_message(reviewer_chat_id, card, reply_markup=kb)
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('UPDATE projects SET review_reviewer_chat_id = ? WHERE project_id = ?', (str(reviewer_chat_id), project_id))
            conn.commit()
            cursor.close()
            conn.close()
        bot.send_message(message.from_user.id, "Проект отправлен на проверку.")
    except Exception as e:
        bot.send_message(message.from_user.id, f"Не удалось отправить проверяющему: {e}")


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith('review:'))
def handle_review_callback(call):
    ensure_user_chat_record(call.message.chat.id)
    parts = call.data.split(':')
    if len(parts) != 3:
        return
    action, project_id_str = parts[1], parts[2]
    try:
        project_id = int(project_id_str)
    except Exception:
        return

    if action == 'approve':
        handle_review_approve(call, project_id)
    elif action == 'reject':
        handle_review_reject(call, project_id)


def handle_review_approve(call, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE projects SET review_approved = 1 WHERE project_id = ?', (project_id,))
        
        cursor.execute('''
            SELECT u.tg_chat_id
            FROM projects p
            JOIN users u ON p.project_leader_id = u.user_id
            WHERE p.project_id = ?
        ''', (project_id,))
        row = cursor.fetchone()
        leader_chat_id = row[0] if row else None
        
        conn.commit()
        cursor.close()
        conn.close()
    
    bot.answer_callback_query(call.id, "Одобрено")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "Проект одобрен.")
    
    if leader_chat_id:
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute('SELECT project_name FROM projects WHERE project_id = ?', (project_id,))
                row = cursor.fetchone()
                project_name = row[0] if row else f"ID: {project_id}"
                cursor.close()
                conn.close()
            

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_yes = types.KeyboardButton("Да, опубликовать")
            btn_no = types.KeyboardButton("Нет, не публиковать")
            markup.add(btn_yes, btn_no)
            
            bot.send_message(leader_chat_id, f"Ваш проект '{project_name}' одобрен проверяющим! Хотите опубликовать его?", reply_markup=markup)
            

            _pending_publication_confirmations[leader_chat_id] = project_id
        except Exception:
            pass


def handle_review_reject(call, project_id):
    _pending_review_comments[call.message.chat.id] = project_id
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "Напишите комментарий для отправки обратно автору:")


@bot.message_handler(func=lambda m: _pending_review_comments.get(m.chat.id) is not None)
def handle_reviewer_comment(message):
    ensure_user_chat_record(message.chat.id)
    project_id = _pending_review_comments.pop(message.chat.id, None)
    if not project_id:
        return
    comment = message.text or ''

    leader_chat_id = None
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('PRAGMA busy_timeout = 5000')
        cursor.execute('UPDATE projects SET review_comment = ?, review_approved = 0 WHERE project_id = ?', (comment, project_id))
        cursor.execute('''
            SELECT u.tg_chat_id
            FROM projects p
            JOIN users u ON p.project_leader_id = u.user_id
            WHERE p.project_id = ?
        ''', (project_id,))
        row = cursor.fetchone()
        if row and row[0]:
            leader_chat_id = row[0]
        conn.commit()
        cursor.close()
        conn.close()

    bot.send_message(message.chat.id, "Комментарий отправлен автору.")
    if leader_chat_id:
        try:
            bot.send_message(leader_chat_id, f"Ваш проект (ID: {project_id}) отправлен на доработку. Комментарий проверяющего:\n\n{comment}")
        except Exception:
            pass


@bot.message_handler(func=lambda m: _pending_publication_confirmations.get(m.chat.id) is not None)
def handle_publication_confirmation(message):
    ensure_user_chat_record(message.chat.id)
    project_id = _pending_publication_confirmations.pop(message.chat.id, None)
    if not project_id:
        return
    
    txt = norm_text(message)
    if txt == "да, опубликовать":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE projects SET project_agreed = 1 WHERE project_id = ?', (project_id,))
            conn.commit()
            cursor.close()
            conn.close()
        bot.send_message(message.chat.id, "Проект будет опубликован автоматически.")
    else:
        bot.send_message(message.chat.id, "Проект не будет опубликован.")
    
    show_main_menu(message)


def publish_project_if_approved(message, project_id):
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('PRAGMA busy_timeout = 5000')
        cursor.execute('SELECT review_approved, project_sent FROM projects WHERE project_id = ?', (project_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

    if not row:
        bot.send_message(message.from_user.id, "Проект не найден.")
        return

    review_approved, project_sent = row
    if project_sent:
        bot.send_message(message.from_user.id, "Проект уже опубликован.")
        show_project_actions(message, project_id)
        return

    if review_approved == 1:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_yes = types.KeyboardButton("Да, опубликовать")
        btn_no = types.KeyboardButton("Нет, отменить")
        markup.add(btn_yes, btn_no)
        
        msg = bot.send_message(message.from_user.id, "Вы уверены, что хотите опубликовать этот проект?", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_manual_publication_confirmation, project_id)
    else:
        bot.send_message(message.from_user.id, "Проект ещё не одобрен проверяющим.")
        show_project_actions(message, project_id)


def handle_manual_publication_confirmation(message, project_id):
    txt = norm_text(message)
    if txt == "да, опубликовать":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('''
                SELECT p.project_name, p.project_description, p.project_need_members, p.project_competencies, p.project_contacts, u.users_name
                FROM projects p
                JOIN users u ON p.project_leader_id = u.user_id
                WHERE p.project_id = ?
            ''', (project_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        
        if not row:
            bot.send_message(message.from_user.id, "Проект не найден.")
            return
            
        name, desc, need_members, competencies, contacts, author_name = row
        message_text = f"🔥 Новый проект!\n\n"
        message_text += f"Название: {name}\n"
        message_text += f"Автор: {author_name}\n"
        message_text += f"Описание: {desc}\n"
        message_text += f"Требуется участников: {need_members}\n"
        message_text += f"Требуемые компетенции: {competencies}\n"
        message_text += f"Контакты: {contacts}\n"
        
        try:
            sent_message = bot.send_message(config.PUBLICATION_CHAT_ID, message_text, message_thread_id=config.PUBLICATION_THREAD_ID)
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute('''
                    UPDATE projects
                    SET project_sent = 1, project_id_message = ?, project_agreed = 1
                    WHERE project_id = ?
                ''', (sent_message.message_id, project_id))
                conn.commit()
                cursor.close()
                conn.close()
            bot.send_message(message.from_user.id, "Проект опубликован.")
            show_project_menu(message)
        except Exception as e:
            bot.send_message(message.from_user.id, f"Ошибка публикации: {e}")
            show_project_actions(message, project_id)
    else:
        bot.send_message(message.from_user.id, "Публикация отменена.")
        show_project_actions(message, project_id)

def check_and_send_projects():
    while True:
       
        rows = []
        try:
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute('''
                    SELECT p.project_id, p.project_name, p.project_description, p.project_need_members, p.project_competencies, p.project_contacts, u.users_name 
                    FROM projects p
                    JOIN users u ON p.project_leader_id = u.user_id
                    WHERE p.project_sent = 0 AND review_approved = 1 AND project_agreed = 1
                ''')
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
        except Exception:
            
            ensure_projects_competencies_column()
            try:
                with db_lock:
                    conn = config.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('PRAGMA busy_timeout = 5000')
                    cursor.execute('''
                        SELECT p.project_id, p.project_name, p.project_description, p.project_need_members, p.project_competencies, p.project_contacts, u.users_name 
                        FROM projects p
                        JOIN users u ON p.project_leader_id = u.user_id
                        WHERE p.project_sent = 0 AND review_approved = 1 AND project_agreed = 1
                    ''')
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()
            except Exception:
                rows = []

        for row in rows:
            project_id, name, desc, need_members, competencies, contacts, author_name = row
            message_text = f"🔥 Новый проект!\n\n"
            message_text += f"Название: {name}\n"
            message_text += f"Автор: {author_name}\n"
            message_text += f"Описание: {desc}\n"
            message_text += f"Требуется участников: {need_members}\n"
            message_text += f"Требуемые компетенции: {competencies}\n"
            message_text += f"Контакты: {contacts}\n"

            try:
                sent_message = bot.send_message(config.PUBLICATION_CHAT_ID, message_text, message_thread_id=config.PUBLICATION_THREAD_ID)
            except Exception:
                continue
            with db_lock:
                conn = config.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('PRAGMA busy_timeout = 5000')
                cursor.execute('''
                    UPDATE projects 
                    SET project_sent = 1, project_id_message = ? 
                    WHERE project_id = ?
                ''', (sent_message.message_id, project_id))
                conn.commit()
                cursor.close()
                conn.close()
            
        time.sleep(15)

project_checker_thread = threading.Thread(target=check_and_send_projects, daemon=True)
project_checker_thread.start()


@bot.message_handler(commands=['start'])
def get_start_info(message):
    ensure_user_chat_record(message.from_user.id)
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('SELECT menu_session FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
            row = cursor.fetchone()
            need_refresh = True
            if row is not None and row[0] == CURRENT_SESSION:
                need_refresh = False
            if need_refresh:
                cursor.execute('UPDATE users SET menu_session = ? WHERE tg_chat_id = ?', (CURRENT_SESSION, str(message.from_user.id)))
                conn.commit()
            cursor.close()
            conn.close()
        if need_refresh:
            show_main_menu(message)
            return
    except Exception:
        pass
    bot.send_message(message.from_user.id, "Привет! Я бот, который поможет тебе найти участников или команду.")
    show_main_menu(message)
    

telebot.apihelper.READ_TIMEOUT = 30
telebot.apihelper.RETRY_ON_ERROR = True

try:
    bot.set_my_commands([
        telebot.types.BotCommand('start', 'Начать'),
        telebot.types.BotCommand('menu', 'Показать меню')
    ])
except Exception:
    pass

@bot.message_handler(commands=['menu'])
def cmd_menu(message):
    ensure_user_chat_record(message.from_user.id)
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('UPDATE users SET menu_session = ? WHERE tg_chat_id = ?', (CURRENT_SESSION, str(message.from_user.id)))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception:
        pass
    show_main_menu(message)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    ensure_user_chat_record(message.from_user.id)
    try:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')
            cursor.execute('SELECT menu_session FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
            row = cursor.fetchone()
            need_refresh = True
            if row is not None and row[0] == CURRENT_SESSION:
                need_refresh = False
            if need_refresh:
                cursor.execute('UPDATE users SET menu_session = ? WHERE tg_chat_id = ?', (CURRENT_SESSION, str(message.from_user.id)))
                conn.commit()
            cursor.close()
            conn.close()
        if need_refresh:
            show_main_menu(message)
            return
    except Exception:
        pass
    #bot.send_message(message, "У бота технические шоколадки, возможны перебои")
    txt = norm_text(message)
    if txt == "заполнить анкету":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT tg_chat_id FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
            user_exists = cursor.fetchone()
            cursor.close()
            conn.close()
        
        if user_exists:
            bot.send_message(message.from_user.id, "Вы уже зарегистрированы в системе!")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_yes = types.KeyboardButton("Да")
            btn_no = types.KeyboardButton("Нет") 
            markup.add(btn_yes, btn_no)
            msg = bot.send_message(message.from_user.id, "Хотите изменить данные?", reply_markup=markup)
            
            def handle_edit_response(message):
                if norm_text(message) == "да":
                    conn = config.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM users WHERE tg_chat_id = ?', (str(message.from_user.id),))
                    user_id = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    edit_account(message, user_id)
                else:
                    show_main_menu(message)
                    
            bot.register_next_step_handler(msg, handle_edit_response)
        else:
            msg = bot.send_message(message.from_user.id, "Отлично! Давай для начала познакомимся. Напиши мне свое ФИО.")
            bot.register_next_step_handler(msg, process_registration_step)
    elif txt == "добавить возможный проект":
        start_possible_project_flow(message)
    elif txt == "q&a":
        q_and_a(message)
    elif txt == "список проектов":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT project_name FROM projects p JOIN users u ON p.project_leader_id = u.user_id WHERE u.tg_chat_id = ?', (str(message.from_user.id),))
            projects = cursor.fetchall()
            cursor.close()
            conn.close()

        if projects:
            response = "Ваши проекты:\n\n"
            for project in projects:
                response += f"• {project[0]}\n"
            bot.send_message(message.from_user.id, response)
        else:
            bot.send_message(message.from_user.id, "Пусто")
        show_project_menu(message)

    elif txt == "добавить проект":
        msg = bot.send_message(message.from_user.id, "Введите название проекта:")
        bot.register_next_step_handler(msg, process_project_name)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        
    elif txt == "назад в меню":
        show_main_menu(message)

    elif txt == "личные данные":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT users_name, users_group, tg_id, birth_date, institute, phone_number, email, social_link
                FROM users WHERE tg_chat_id = ?
            ''', (str(message.from_user.id),))
            user_row = cursor.fetchone()
            cursor.close()
            conn.close()

        if user_row:
            users_name, users_group, tg_id, birth_date, institute, phone_number, email, social_link = user_row
            response = "Ваши данные:\n\n"
            response += f"Ф.И.О.: {users_name or ''}\n"
            response += f"Дата рождения: {birth_date or ''}\n"
            response += f"Институт: {institute or ''}\n"
            response += f"Академическая группа: {users_group or ''}\n"
            response += f"Номер мобильного телефона: {phone_number or ''}\n"
            response += f"Электронная почта: {email or ''}\n"
            response += f"Ссылка на страницу в социальных сетях: {social_link or ''}\n"
            bot.send_message(message.from_user.id, response)
        else:
            bot.send_message(message.from_user.id, "Вы еще не зарегистрированы в системе. Используйте команду 'Заполнить анкету' для регистрации.")
    else:
        bot.send_message(message.from_user.id, "Извини, я тебя не понимаю")

bot.polling(none_stop=True, interval=0)