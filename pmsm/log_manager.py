# log_manager.py
import sqlite3
import re
from datetime import datetime, timedelta
import time
import threading
import pytz

class LogManager:
    def __init__(self, db_path="logs.db"):
        self.db_path = db_path
        self.log_pattern = re.compile(r'\[([\d:]+)\] \[([^/]+)/([^]]+)\]: (.+)')
        self.lock = threading.Lock()
        self.timezone = pytz.timezone('Asia/Shanghai')  # 设置为 UTC+8
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
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS instance_states (
                        instance_name TEXT PRIMARY KEY,
                        pid INTEGER,
                        start_id INTEGER,
                        start_time DATETIME
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

    def _get_current_time(self):
        """获取当前UTC+8时间"""
        return datetime.now(pytz.UTC).astimezone(self.timezone)

    def new_instance_start(self, instance_name):
        """创建新的实例启动记录"""
        with self.lock:
            conn = self._get_connection()
            try:
                # 开始事务
                conn.execute('BEGIN TRANSACTION')
                
                # 使用UTC+8时间
                start_time = self._get_current_time().strftime('%Y-%m-%d %H:%M:%S')
                cursor = conn.execute(
                    'INSERT INTO instance_starts (instance_name, start_time) VALUES (?, ?)',
                    (instance_name, start_time)
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
        if (match):
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
                    # 将日志时间转换为UTC+8
                    current_time = self._get_current_time()
                    log_time = current_time.replace(
                        hour=int(parsed['timestamp'].split(':')[0]),
                        minute=int(parsed['timestamp'].split(':')[1]),
                        second=int(parsed['timestamp'].split(':')[2])
                    )
                    
                    conn.execute(f'''
                        INSERT INTO {table_name} 
                        (timestamp, thread, level, message, log_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        parsed['timestamp'],
                        parsed['thread'],
                        parsed['level'],
                        parsed['message'],
                        log_time.strftime('%Y-%m-%d %H:%M:%S')
                    ))
                else:
                    # 对于不匹配模式的日志，使用当前时间
                    current_time = self._get_current_time()
                    conn.execute(f'''
                        INSERT INTO {table_name} 
                        (timestamp, thread, level, message, log_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        current_time.strftime('%H:%M:%S'),
                        'System',
                        'INFO',

                        log_line,
                        current_time.strftime('%Y-%m-%d %H:%M:%S')
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

    def _convert_wildcard_to_sql(self, pattern):
        """将通配符模式转换为SQL LIKE模式"""
        # 先转义所有特殊字符
        escaped = pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        # 将未转义的 * 转换为 %
        result = ''
        i = 0
        while i < len(escaped):
            if escaped[i:i+2] == '\\*':  # 转义的 *
                result += '*'
                i += 2
            elif escaped[i] == '*':  # 未转义的 *
                result += '%'
                i += 1
            else:
                result += escaped[i]
                i += 1
        return result

    def _convert_search_pattern(self, pattern):
        """转换搜索模式为SQL LIKE模式"""
        if not pattern:
            return None
        # 替换未转义的 * 为 %，保留转义的 \*
        i = 0
        result = ''
        while i < len(pattern):
            if pattern[i:i+2] == '\\*':
                result += '*'
                i += 2
            elif pattern[i] == '*':
                result += '%'
                i += 1
            else:
                result += pattern[i]
                i += 1
        return f'%{result}%'  # 在两端添加通配符以支持部分匹配

    def get_logs(self, instance_name, start_id=None, start_id_range=None, 
                 start_time=None, end_time=None, search_pattern=None):
        """获取日志记录，支持多种筛选条件"""
        with self.lock:
            conn = self._get_connection()
            try:
                # 获取启动记录
                if start_id is not None:  # 使用 is not None 避免 start_id = 0 的情况
                    query = '''
                        SELECT id, start_time 
                        FROM instance_starts 
                        WHERE instance_name = ? AND id = ?
                    '''
                    cursor = conn.execute(query, (instance_name, start_id))
                    start_ids = cursor.fetchall()
                elif start_id_range:
                    start_min, start_max = start_id_range
                    query = '''
                        SELECT id, start_time 
                        FROM instance_starts 
                        WHERE instance_name = ? AND id BETWEEN ? AND ?
                        ORDER BY id DESC
                    '''
                    cursor = conn.execute(query, (instance_name, start_min, start_max))
                    start_ids = cursor.fetchall()
                else:
                    # 默认获取最后一次启动的日志
                    query = '''
                        SELECT id, start_time 
                        FROM instance_starts 
                        WHERE instance_name = ?
                        ORDER BY id DESC
                        LIMIT 1
                    '''
                    cursor = conn.execute(query, (instance_name,))
                    result = cursor.fetchone()
                    start_ids = [result] if result else []

                print(f"Found start records: {start_ids}")  # 调试输出

                if not start_ids:
                    return []

                all_logs = []
                for start_id, start_time_db in start_ids:
                    table_name = self._get_table_name(instance_name, start_id)
                    if not self._table_exists(conn, table_name):
                        continue

                    conditions = []
                    params = []
                    
                    if start_time:
                        conditions.append("log_time >= ?")
                        params.append(start_time)
                    if end_time:
                        conditions.append("log_time <= ?")
                        params.append(end_time)
                    if search_pattern:
                        # 转换搜索模式
                        sql_pattern = self._convert_search_pattern(search_pattern)
                        print(f"Search pattern: {search_pattern} -> SQL pattern: {sql_pattern}")  # 调试输出
                        if sql_pattern:
                            conditions.append("message LIKE ?")  # 只搜索消息内容
                            params.append(sql_pattern)

                    query = f'''
                        SELECT timestamp, thread, level, message, log_time 
                        FROM {table_name}
                        {" WHERE " + " AND ".join(conditions) if conditions else ""}
                        ORDER BY id ASC
                    '''
                    
                    print(f"Executing query: {query} with params: {params}")  # 调试输出

                    cursor = conn.execute(query, params)
                    logs = cursor.fetchall()
                    
                    all_logs.extend([{
                        'timestamp': log[0],
                        'thread': log[1],
                        'level': log[2],
                        'message': log[3],
                        'log_time': log[4],
                        'start_id': start_id,
                        'start_time': start_time_db
                    } for log in logs])

                return all_logs

            finally:
                conn.close()

    def update_instance_state(self, instance_name, state):
        """更新实例状态到数据库"""
        with self.lock:
            conn = self._get_connection()
            try:
                conn.execute('''
                    INSERT INTO instance_states (instance_name, pid, start_id, start_time)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(instance_name) DO UPDATE SET
                    pid=excluded.pid,
                    start_id=excluded.start_id,
                    start_time=excluded.start_time
                ''', (instance_name, state["pid"], state["start_id"], state["start_time"]))
                conn.commit()
            finally:
                conn.close()

    def get_instance_state(self, instance_name):
        """从数据库获取实例状态"""
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute('''
                    SELECT pid, start_id, start_time
                    FROM instance_states
                    WHERE instance_name = ?
                ''', (instance_name,))
                result = cursor.fetchone()
                if result:
                    return {
                        "pid": result[0],
                        "start_id": result[1],
                        "start_time": result[2]
                    }
                return None
            finally:
                conn.close()

    def remove_instance_state(self, instance_name):
        """从数据库移除实例状态"""
        with self.lock:
            conn = self._get_connection()
            try:
                conn.execute('''
                    DELETE FROM instance_states
                    WHERE instance_name = ?
                ''', (instance_name,))
                conn.commit()
            finally:
                conn.close()