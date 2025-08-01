# get_character_full_data.py
import sqlite3
from flask import g

# 数据库文件名
DB_FILE = "chat_data.db"
class SimpleDatabase:
    """
    一个简单的 SQLite 数据库包装类。
    这个类的每个实例代表一个独立的数据库连接。
    """

    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        # 连接数据库并设置 row_factory 以便获取类似字典的行数据
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def close(self):
        """关闭数据库连接。"""
        if self.conn is not None:
            self.conn.close()

    def get_cursor(self):
        """获取数据库游标。"""
        return self.conn.cursor()

    def create_tables(self):
        """如果表不存在，则创建它们。"""
        cursor = self.get_cursor()
        # 聊天记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message_type TEXT NOT NULL, -- 'human' or 'ai'
                content TEXT,
                image_url TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 朋友圈动态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_db_id TEXT NOT NULL, -- e.g., "char_1"
                content TEXT,
                image_url TEXT,
                tags TEXT, -- 存储为逗号分隔的字符串
                post_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 日记条目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_db_id TEXT NOT NULL, -- e.g., "char_1"
                content TEXT NOT NULL,
                date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_chat_message(self, conversation_id, message_type, content, image_url=None):
        """添加一条聊天记录。"""
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO chat_history (conversation_id, message_type, content, image_url) VALUES (?, ?, ?, ?)",
            (conversation_id, message_type, content, image_url)
        )
        self.conn.commit()

    def get_chat_history(self, conversation_id):
        """根据会话ID获取聊天记录。"""
        cursor = self.get_cursor()
        cursor.execute(
            "SELECT * FROM chat_history WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
        # 将 Row 对象转换为标准字典，以便进行 JSON 序列化
        return [dict(row) for row in cursor.fetchall()]

    def get_all_social_posts(self, character_db_id):
        """获取指定角色的所有朋友圈动态。"""
        cursor = self.get_cursor()
        cursor.execute(
            "SELECT * FROM social_posts WHERE character_db_id = ? ORDER BY post_time DESC",
            (character_db_id,)
        )
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            # 将标签字符串转换为数组以匹配前端需求
            post['tags'] = post['tags'].split(',') if post.get('tags') else []
            posts.append(post)
        return posts

    def get_all_diaries(self, character_db_id):
        """获取指定角色的所有日记。"""
        cursor = self.get_cursor()
        cursor.execute(
            "SELECT * FROM diary_entries WHERE character_db_id = ? ORDER BY date DESC",
            (character_db_id,)
        )
        return [dict(row) for row in cursor.fetchall()]



    def add_social_post(self, character_db_id, content, tags, post_time, image_url=None):
        """
        添加一条新的朋友圈动态。

        :param character_db_id: 发布动态的角色ID。
        :param content: 动态的文本内容。
        :param tags: 动态的标签（list[str]类型）。
        :param post_time: 动态的发布时间。
        :param image_url: 动态附带的图片URL（可选）。
        """
        # 如果tags是列表，则转换为逗号分隔的字符串
        if isinstance(tags, list):
            tags = ','.join(tags)
        
        cursor = self.get_cursor()
        cursor.execute(
            """
            INSERT INTO social_posts (character_db_id, content, tags, post_time, image_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (character_db_id, content, tags, post_time, image_url)
        )
        self.conn.commit()

    def add_diary_entry(self, character_db_id, content):
        """
        添加一篇新的日记。
        日期将自动设置为当前时间戳。

        :param character_db_id: 写日记的角色ID。
        :param content: 日记的内容。
        """
        cursor = self.get_cursor()
        cursor.execute(
            "INSERT INTO diary_entries (character_db_id, content) VALUES (?, ?)",
            (character_db_id, content)
        )
        self.conn.commit()

    def get_social_posts(self, character_db_id):
        """
        获取指定角色的所有社交动态。

        :param character_db_id: 角色ID。
        :return: 包含所有社交动态的列表，每个动态的tags字段为list[str]类型。
        """
        cursor = self.get_cursor()
        cursor.execute(
            "SELECT * FROM social_posts WHERE character_db_id = ? ORDER BY post_time DESC",
            (character_db_id,)
        )
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            # 将tags字符串转换为列表
            if post['tags']:
                post['tags'] = post['tags'].split(',')
            else:
                post['tags'] = []
            posts.append(post)
        return posts

    # ====================================================================
    # 新增方法 END
    # ====================================================================


def get_db():
    """
    为当前应用上下文打开一个新的数据库连接（如果尚不存在）。
    """
    if 'simple_db' not in g:
        g.simple_db = SimpleDatabase()
    return g.simple_db
