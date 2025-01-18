# log_manager.py
import sqlite3
import re
from datetime import datetime
import time
import threading

class LogManager:
    def __init__(self, db_path="logs.db"):
        self.db_path = db_path
        self.log_pattern = re.compile(r'\[([\d:]+)\] \[([^/]+)/([^]]+)\]: (.+)')
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        """获取数据库连接，带有重试机制"""
        retries = 5
        while retries > 0:
            try:
                conn = sqlite3.connect(self.db_path, timeout=20)
                return conn
            except sqlite3.OperationalError as e:
                retries -= 1
                if retries == 0:
                    raise e
                time.sleep(1)

    def _init_db(self):
        """初始化数据库"""
        with self.lock:
            conn = self._get_connection()
            try:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS instance_starts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instance_name TEXT NOT NULL,
                        start_time DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            finally:
                conn.close()

    def _create_log_table(self, table_name):
        """创建日志表"""
        with self.lock:
            conn = self._get_connection()
            try:
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        thread TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        log_time DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            finally:
                conn.close()

    def _get_table_name(self, instance_name, start_id):
        return f"logs_{instance_name}_{start_id}"

    def new_instance_start(self, instance_name):
        """创建新的实例启动记录"""
        with self.lock:
            conn = self._get_connection()
            try:
                # 开始事务
                conn.execute('BEGIN TRANSACTION')
                
                # 插入启动记录
                cursor = conn.execute(
                    'INSERT INTO instance_starts (instance_name) VALUES (?)',
                    (instance_name,)
                )
                start_id = cursor.lastrowid
                
                # 创建日志表
                table_name = self._get_table_name(instance_name, start_id)
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        thread TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        log_time DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 提交事务
                conn.commit()
                return start_id
            except Exception as e:
                conn.rollback()
                print(f"Error creating new instance start: {e}")
                raise
            finally:
                conn.close()

    def parse_log_line(self, line):
        match = self.log_pattern.match(line)
        if match:
            time, thread, level, message = match.groups()
            return {
                'timestamp': time,
                'thread': thread,
                'level': level,
                'message': message
            }
        return None

    def add_log(self, instance_name, start_id, log_line):
        """添加日志记录"""
        if not isinstance(start_id, int):
            print(f"Warning: Invalid start_id: {start_id}")
            return

        with self.lock:
            conn = self._get_connection()
            try:
                table_name = self._get_table_name(instance_name, start_id)
                
                # 确保表存在
                if not self._table_exists(conn, table_name):
                    self._create_log_table(table_name)
                
                parsed = self.parse_log_line(log_line)
                if parsed:
                    conn.execute(f'''
                        INSERT INTO {table_name} 
                        (timestamp, thread, level, message)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        parsed['timestamp'],
                        parsed['thread'],
                        parsed['level'],
                        parsed['message']
                    ))
                else:
                    # 对于不匹配模式的日志，使用默认值
                    current_time = datetime.now().strftime('%H:%M:%S')
                    conn.execute(f'''
                        INSERT INTO {table_name} 
                        (timestamp, thread, level, message)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        current_time,
                        'System',
                        'INFO',
                        log_line
                    ))
                conn.commit()
            finally:
                conn.close()

    def _table_exists(self, conn, table_name):
        """检查表是否存在"""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None

    def get_logs(self, instance_name, start_time=None):
        """获取日志记录"""
        with self.lock:
            conn = self._get_connection()
            try:
                print(f"Getting logs for instance: {instance_name}")
                # 获取最近的启动记录
                cursor = conn.execute('''
                    SELECT id, start_time 
                    FROM instance_starts 
                    WHERE instance_name = ?
                    ORDER BY id DESC
                ''', (instance_name,))
                
                start_ids = cursor.fetchall()
                print(f"Found {len(start_ids)} start records")
                
                all_logs = []
                for start_id, start_time_db in start_ids:
                    table_name = self._get_table_name(instance_name, start_id)
                    print(f"Processing logs from table: {table_name}")
                    
                    if not self._table_exists(conn, table_name):
                        print(f"Creating missing table: {table_name}")
                        self._create_log_table(table_name)
                        
                    query = f'''
                        SELECT timestamp, thread, level, message, log_time 
                        FROM {table_name}
                        {" WHERE log_time >= ?" if start_time else ""}
                        ORDER BY id DESC
                    '''
                    
                    try:
                        cursor = conn.execute(query, (start_time,) if start_time else ())
                        logs = cursor.fetchall()
                        print(f"Found {len(logs)} logs in table {table_name}")
                        
                        all_logs.extend([{
                            'timestamp': log[0],
                            'thread': log[1],
                            'level': log[2],
                            'message': log[3],
                            'log_time': log[4]
                        } for log in logs])
                    except sqlite3.OperationalError as e:
                        print(f"Error querying table {table_name}: {e}")
                        continue
                
                return all_logs
            finally:
                conn.close()