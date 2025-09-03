import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()

    # Таблица пользователей: id, имя, роль
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'client'
    )
    """)

    # Таблица заявок: id, id клиента, описание, статус, id исполнителя, фото до/после, даты
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        req_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        problem_text TEXT NOT NULL,
        status TEXT DEFAULT 'new', -- new, assigned, in_progress, done, confirmed
        assigned_to INTEGER DEFAULT NULL,
        photo_before TEXT DEFAULT NULL,
        photo_after TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP DEFAULT NULL,
        FOREIGN KEY (client_id) REFERENCES users (user_id),
        FOREIGN KEY (assigned_to) REFERENCES users (user_id)
    )
    """)

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def add_user(user_id, username, full_name, role='client'):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    # Добавляем пользователя, если его еще нет
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, role) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, role))
    conn.commit()
    conn.close()

def update_user_role(user_id, new_role):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

def add_request(client_id, problem_text, photo_before=None):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO requests (client_id, problem_text, photo_before)
    VALUES (?, ?, ?)
    """, (client_id, problem_text, photo_before))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def get_requests(status=None, user_id=None, role=None):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    query = "SELECT * FROM requests"
    params = []

    if status and role == 'manager':
        query += " WHERE status = ?"
        params.append(status)
    elif role == 'master': # Мастер видит только свои назначенные заявки
        query += " WHERE assigned_to = ?"
        params.append(user_id)
        if status:
            query += " AND status = ?"
            params.append(status)
    elif role == 'client': # Клиент видит только свои заявки
        query += " WHERE client_id = ?"
        params.append(user_id)
        if status:
            query += " AND status = ?"
            params.append(status)

    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    requests = cur.fetchall()
    conn.close()
    return requests

def assign_request(req_id, master_id):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    cur.execute("UPDATE requests SET status = 'assigned', assigned_to = ? WHERE req_id = ?", (master_id, req_id))
    conn.commit()
    conn.close()

def update_request_status(req_id, status, photo_after=None):
    conn = sqlite3.connect('bot_data.db')
    cur = conn.cursor()
    if status == 'done':
        cur.execute("UPDATE requests SET status = ?, photo_after = ?, finished_at = ? WHERE req_id = ?",
                    (status, photo_after, datetime.now(), req_id))
    else:
        cur.execute("UPDATE requests SET status = ? WHERE req_id = ?", (status, req_id))
    conn.commit()
    conn.close()

# Инициализируем БД при импорте
init_db()
