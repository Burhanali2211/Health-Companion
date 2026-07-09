import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "health_vault.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    # Create Users Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            blood_type TEXT,
            allergies TEXT,
            chronic_conditions TEXT,
            emergency_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create Health Logs Table (for blood pressure, sugar, mood)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log_type TEXT NOT NULL,
            log_value TEXT NOT NULL,
            notes TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def create_user(name, age=None, blood_type="", allergies="", chronic_conditions="", emergency_contact=""):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (name, age, blood_type, allergies, chronic_conditions, emergency_contact)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, age, blood_type, allergies, chronic_conditions, emergency_contact))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id

def get_all_users():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY name")
    users = [dict(row) for row in cur.fetchall()]
    conn.close()
    return users

def get_user(user_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def add_health_log(user_id, log_type, log_value, notes=""):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO health_logs (user_id, log_type, log_value, notes)
        VALUES (?, ?, ?, ?)
    ''', (user_id, log_type, str(log_value), notes))
    conn.commit()
    conn.close()

def get_health_logs(user_id, limit=50):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM health_logs 
        WHERE user_id = ? 
        ORDER BY logged_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    logs = [dict(row) for row in cur.fetchall()]
    conn.close()
    return logs
