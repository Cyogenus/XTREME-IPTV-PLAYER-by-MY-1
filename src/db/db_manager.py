import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='iptv_player.db'):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                server TEXT,
                username TEXT,
                password TEXT,
                login_type TEXT NOT NULL, -- 'xtream' or 'm3u'
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_profile(self, name, server, username, password, login_type):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO profiles (name, server, username, password, login_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, server, username, password, login_type))
        conn.commit()
        conn.close()

    def get_profiles(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles ORDER BY created_at DESC')
        rows = cursor.fetchall()
        profiles = [dict(row) for row in rows]
        conn.close()
        return profiles

    def delete_profile(self, profile_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM profiles WHERE id = ?', (profile_id,))
        conn.commit()
        conn.close()
