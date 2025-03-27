import config
import sqlite3
import telebot
from telebot import types
from threading import Lock
import time
import threading


# Создаем блокировку для блядского потокобезопасного доступа к БД без которого эта конина не будет работаь
db_lock = Lock()

# Глобальная переменная для хранения названия проекта
current_project_name = None

bot = telebot.TeleBot(config.token)
config.check_database_state()

def process_name_step(message):
    # Сохраняем ФИО пользователя в базу данных
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (tg_id, users_name, users_group, tg_chat_id) VALUES (?, ?, ?, ?)', 
                      (str(message.from_user.id), message.text, "", str(message.chat.id)))
        conn.commit()
        cursor.close()
        conn.close()
    
    msg = bot.send_message(message.from_user.id, "Приятно познакомиться :) Из какой ты группы? Если вы преподаватель, напишите: Я преподаватель.")
    bot.register_next_step_handler(msg, process_group_step)

def process_group_step(message):
    # Добавляем группу пользователя
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET users_group = ? WHERE tg_id = ?',
                      (message.text, str(message.from_user.id)))
        conn.commit()
        cursor.close()
        conn.close()
    
    bot.send_message(message.from_user.id, "Понял! ")

def process_project_name(message):
    project_name = message.text
    msg = bot.send_message(message.from_user.id, "Введите описание проекта:")
    bot.register_next_step_handler(msg, process_project_description, project_name)

def process_project_description(message, project_name):
    project_description = message.text
    msg = bot.send_message(message.from_user.id, "Введите контактные данные:")
    bot.register_next_step_handler(msg, save_project, project_name, project_description)

def save_project(message, project_name, project_description):
    project_contacts = message.text
    
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        # First get the user_id from users table using tg_id
        cursor.execute('SELECT user_id FROM users WHERE tg_id = ?', (str(message.from_user.id),))
        user_id = cursor.fetchone()[0]
        
        cursor.execute('''INSERT INTO projects 
                         (project_leader_id, project_name, project_description, project_contacts)
                         VALUES (?, ?, ?, ?)''',
                      (user_id, project_name, project_description, project_contacts))
        project_id = cursor.execute('SELECT project_id FROM projects WHERE project_leader_id = ? AND project_name = ?', (user_id, project_name)).fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
    
    bot.send_message(message.from_user.id, "Проект успешно добавлен!")
    agreement_on_sending(message, project_id)

def agreement_on_sending(message, project_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_yes = types.KeyboardButton("Да")
    btn_no = types.KeyboardButton("Нет") 
    markup.add(btn_yes, btn_no)
    
    msg = bot.send_message(message.from_user.id, "Хотите ли вы опубликовать свой проект?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_agreement_response, project_id)

def process_agreement_response(message, project_id):

    if message.text == "Да":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE projects SET project_agreed = TRUE WHERE project_id = ?', (project_id,))
            conn.commit()
            cursor.close()
            conn.close()
        bot.send_message(message.from_user.id, "Отлично! Ваш проект будет опубликован в ближайшее время.")
    else:
        bot.send_message(message.from_user.id, "Хорошо, проект не будет опубликован.")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton("Добавить проект")
    btn_back = types.KeyboardButton("Назад в меню")
    markup.row(btn_add)
    markup.row(btn_back)
    bot.send_message(message.from_user.id, "Введите 'Добавить проект' или нажмите 'Назад в меню' для возврата в меню", reply_markup=markup)

def edit_project(message, project_id):
    bot.send_message(message.from_user.id, "Этот раздел еше недоступен. Вернитесь позже.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Заполнить анкету")
    btn5 = types.KeyboardButton("Личные данные")
    btn2 = types.KeyboardButton("Добавить кейс хакатона")
    btn3 = types.KeyboardButton("Список проектов")
    btn4 = types.KeyboardButton("Шутка")
    markup.row(btn1, btn5)
    markup.row(btn3, btn4)
    markup.row(btn2)
    bot.send_message(message.from_user.id, "Вы вернулись в главное меню", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Выбрать проект")
def project_choice(message):
    bot.send_message(message.from_user.id, "Напишите название проекта:")
    bot.register_next_step_handler(message, search_project_name)

def search_project_name(message):
    
    with db_lock:
        conn = config.get_db_connection()
        cursor = conn.cursor()
        project_name = message.text
        cursor.execute('SELECT user_id FROM users WHERE tg_id = ?', (str(message.from_user.id),))
        user_id_result = cursor.fetchone()
        
        if user_id_result is None:
            bot.send_message(message.from_user.id, "Пользователь не найден")
            cursor.close()
            conn.close()
            return
            
        user_id = user_id_result[0]
        cursor.execute('SELECT project_id FROM projects WHERE project_leader_id = ? AND project_name = ?', (user_id, project_name))
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
    btn_back = types.KeyboardButton("Назад")
    markup.row(btn_edit, btn_publish)
    markup.row(btn_back)
    
    def handle_project_action(m):
        if m.text == "Изменить проект":
            edit_project(m, project_id)
        elif m.text == "Опубликовать проект":
            agreement_on_sending(m, project_id)
        elif m.text == "Назад":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_add = types.KeyboardButton("Добавить проект")
            btn_chs = types.KeyboardButton("Выбрать проект")
            btn_back = types.KeyboardButton("Назад в меню")
            markup.row(btn_add)
            markup.row(btn_chs)
            markup.row(btn_back)
            bot.send_message(message.from_user.id, "Введите 'Добавить проект' или нажмите 'Назад в меню' для возврата в меню", reply_markup=markup)
    
    bot.register_next_step_handler(message, handle_project_action)
    bot.send_message(message.from_user.id, "Выберите действие:", reply_markup=markup)

def check_and_send_projects():
    while True:
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            
            # Получаем неотправленные проекты
            cursor.execute('''
                SELECT p.*, u.users_name 
                FROM projects p
                JOIN users u ON p.project_leader_id = u.user_id
                WHERE p.project_sent = 0 AND project_agreed = 1
            ''')
            projects = cursor.fetchall()
            
            for project in projects:
                # Формируем сообщение для канала
                message_text = f"🔥 Новый проект!\n\n"
                message_text += f"Название: {project[2]}\n"
                message_text += f"Автор: {project[-1]}\n"  # users_name из JOIN
                message_text += f"Описание: {project[3]}\n"
                message_text += f"Требуется участников: {project[4]}\n"
                message_text += f"Требуемые специальности: {project[5]}\n"
                message_text += f"Контакты: {project[7]}\n"

                # Отправляем в канал
                sent_message = bot.send_message(config.PUBLICATION_CHAT_ID, message_text, message_thread_id=20)
                
                # Обновляем статус проекта
                cursor.execute('''
                    UPDATE projects 
                    SET project_sent = 1, project_id_message = ? 
                    WHERE project_id = ?
                ''', (sent_message.message_id, project[0]))
                
                conn.commit()
            
            cursor.close()
            conn.close()
            
        # Ждем 1 минуту перед следующей проверкой
        time.sleep(15)

project_checker_thread = threading.Thread(target=check_and_send_projects, daemon=True)
project_checker_thread.start()


@bot.message_handler(commands=['start'])
def get_start_info(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Заполнить анкету")
    btn5 = types.KeyboardButton("Личные данные")
    btn2 = types.KeyboardButton("Добавить кейс хакатона")
    btn3 = types.KeyboardButton("Список проектов")
    btn4 = types.KeyboardButton("Шутка")
    markup.row(btn1, btn5)
    markup.row(btn3, btn4)
    markup.row(btn2)
    bot.send_message(message.from_user.id, "Привет! Я бот, который поможет тебе найти участников или команду.", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "Заполнить анкету":
        # Проверяем есть ли пользователь в базе данных
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT tg_id FROM users WHERE tg_id = ?', (str(message.from_user.id),))
            user_exists = cursor.fetchone()
            cursor.close()
            conn.close()
        
        if user_exists:
            bot.send_message(message.from_user.id, "Вы уже зарегистрированы в системе!")
        else:
            msg = bot.send_message(message.from_user.id, "Отлично! Давай для начала познакомимся. Напиши мне свое ФИО.")
            bot.register_next_step_handler(msg, process_name_step)
    elif message.text == "Добавить кейс хакатона":
        bot.send_message(message.from_user.id, "В разработке :)")
    elif message.text == "Шутка":
        bot.send_message(message.from_user.id, "Колобок повесился.")
    elif message.text == "Список проектов":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_add = types.KeyboardButton("Добавить проект")
        btn_chs = types.KeyboardButton("Выбрать проект")
        btn_back = types.KeyboardButton("Назад в меню")
        markup.row(btn_add)
        markup.row(btn_chs)
        markup.row(btn_back)
        bot.send_message(message.from_user.id, "Введите 'Добавить проект' или нажмите 'Назад в меню' для возврата в меню", reply_markup=markup)

        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT project_name FROM projects p JOIN users u ON p.project_leader_id = u.user_id WHERE u.tg_id = ?', (str(message.from_user.id),))
            projects = cursor.fetchall()
            cursor.close()
            conn.close()

        if projects:
            response = "Ваши проекты:\n\n"
            for project in projects:
                response += f"• {project[0]}\n"
            bot.send_message(message.from_user.id, response, reply_markup=markup)
        else:
            bot.send_message(message.from_user.id, "Пусто", reply_markup=markup)

    elif message.text == "Добавить проект":
        msg = bot.send_message(message.from_user.id, "Введите название проекта:")
        bot.register_next_step_handler(msg, process_project_name)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        
    elif message.text == "Назад в меню":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Заполнить анкету")
        btn5 = types.KeyboardButton("Личные данные")
        btn2 = types.KeyboardButton("Добавить кейс хакатона")
        btn3 = types.KeyboardButton("Список проектов")
        btn4 = types.KeyboardButton("Шутка")
        markup.row(btn1, btn5)
        markup.row(btn3, btn4)
        markup.row(btn2)
        bot.send_message(message.from_user.id, "Вы вернулись в главное меню", reply_markup=markup)


        #bot.send_message(message.from_user.id, "В разработке :) Добавится раньше, чем добавление кейса хакатона")
    elif message.text == "Личные данные":
        with db_lock:
            conn = config.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE tg_id = ?', (str(message.from_user.id),))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()

        if user_data:
            response = "Ваши данные:\n\n"
            response += f"ФИО: {user_data[2]}\n"
            response += f"Группа: {user_data[3]}\n" 
            response += f"Контакты: t.me/{user_data[1]}"
            bot.send_message(message.from_user.id, response)
        else:
            bot.send_message(message.from_user.id, "Вы еще не зарегистрированы в системе. Используйте команду 'Заполнить анкету' для регистрации.")
    else:
        bot.send_message(message.from_user.id, "Извини, я тебя не понимаю")


bot.polling(none_stop=True, interval=0)