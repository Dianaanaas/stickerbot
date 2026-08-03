# database.py
# Простое хранилище обращений на SQLite. Не требует установки отдельного сервера БД.

import sqlite3
from datetime import datetime

DB_NAME = "support.db"


def init_db():
    """Создаёт таблицы при первом запуске бота."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            category TEXT,
            order_number TEXT,
            message TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_ticket(user_id, username, category, order_number, message):
    """Сохраняет новое обращение и возвращает его ID."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO tickets (user_id, username, category, order_number, message, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, username, category, order_number, message, datetime.now().isoformat())
    )
    conn.commit()
    ticket_id = cur.lastrowid
    conn.close()
    return ticket_id


def close_ticket(ticket_id):
    """Отмечает обращение как закрытое (например, командой /close в админ-чате)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE tickets SET status='closed' WHERE id=?", (ticket_id,))
    conn.commit()
    conn.close()


def get_open_tickets():
    """Возвращает список всех открытых обращений."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, username, category, order_number, message, created_at FROM tickets WHERE status='open'")
    rows = cur.fetchall()
    conn.close()
    return rows
