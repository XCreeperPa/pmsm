# log_manager.py
import sqlite3
from datetime import datetime

class LogManager:
    def __init__(self, db_path="logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            ''')

    def add_log(self, instance_name, level, message):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO logs (instance_name, level, message)
                VALUES (?, ?, ?)
            ''', (instance_name, level, message))

    def get_logs(self, instance_name, start_time=None):
        query = '''
            SELECT timestamp, level, message
            FROM logs
            WHERE instance_name = ?
        '''
        params = [instance_name]
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            logs = []
            for row in cursor:
                logs.append({
                    "timestamp": row[0],
                    "level": row[1],
                    "message": row[2]
                })
            return logs