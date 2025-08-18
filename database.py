# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="stream_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Table for authorized users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY
            )
        ''')
        # Table for active streams
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streams (
                stream_id TEXT PRIMARY KEY,
                m3u8_link TEXT,
                rtmp_url TEXT,
                stream_key TEXT,
                stream_title TEXT,
                logo_url TEXT,
                text_overlay TEXT,
                start_time TEXT
            )
        ''')
        self.conn.commit()

    def add_user(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (telegram_id) VALUES (?)", (telegram_id,))
        self.conn.commit()

    def remove_user(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        self.conn.commit()

    def is_authorized(self, telegram_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
        return cursor.fetchone() is not None

    def add_stream(self, stream_id, m3u8_link, rtmp_url, stream_key, stream_title, logo_url, text_overlay):
        cursor = self.conn.cursor()
        start_time = datetime.utcnow().isoformat()
        cursor.execute('''
            INSERT INTO streams (stream_id, m3u8_link, rtmp_url, stream_key, stream_title, logo_url, text_overlay, start_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (stream_id, m3u8_link, rtmp_url, stream_key, stream_title, logo_url, text_overlay, start_time))
        self.conn.commit()

    def get_stream(self, stream_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM streams WHERE stream_id = ?", (stream_id,))
        return cursor.fetchone()

    def get_all_streams(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM streams")
        return cursor.fetchall()

    def remove_stream(self, stream_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM streams WHERE stream_id = ?", (stream_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
