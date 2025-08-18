# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('streams.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streams (
                stream_id TEXT PRIMARY KEY,
                m3u8_link TEXT,
                rtmp_url TEXT,
                stream_key TEXT,
                stream_title TEXT,
                user_id INTEGER,
                start_time TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authorized_users (
                telegram_id INTEGER PRIMARY KEY
            )
        ''')
        self.conn.commit()

    def add_stream(self, stream_id, m3u8_link, rtmp_url, stream_key, stream_title, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO streams (stream_id, m3u8_link, rtmp_url, stream_key, stream_title, user_id, start_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (stream_id, m3u8_link, rtmp_url, stream_key, stream_title, user_id, datetime.utcnow()))
        self.conn.commit()

    def get_all_streams(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM streams')
        return cursor.fetchall()

    def get_user_streams(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM streams WHERE user_id = ?', (user_id,))
        return cursor.fetchall()

    def get_stream(self, stream_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM streams WHERE stream_id = ?', (stream_id,))
        return cursor.fetchone()

    def remove_stream(self, stream_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM streams WHERE stream_id = ?', (stream_id,))
        self.conn.commit()

    def add_user(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO authorized_users (telegram_id) VALUES (?)', (telegram_id,))
        self.conn.commit()

    def remove_user(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM authorized_users WHERE telegram_id = ?', (telegram_id,))
        self.conn.commit()

    def is_authorized(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM authorized_users WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone() is not None

    def __del__(self):
        self.conn.close()
