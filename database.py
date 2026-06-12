"""
🗄️ دیتابیس - ذخیره‌سازی داده‌های کاربران
"""

import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "job_ai.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ایجاد جداول"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # جدول کاربران
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                bio TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # جدول کانال‌ها
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                channel_username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_username)
            )
        """)
        
        # جدول تنظیمات
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY(user_id, key)
            )
        """)
        
        # جدول آمار
        c.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id TEXT PRIMARY KEY,
                total_scans INTEGER DEFAULT 0,
                total_matches INTEGER DEFAULT 0,
                last_scan TIMESTAMP
            )
        """)
        
        # جدول شغل‌های یافت شده (جلوگیری از تکرار)
        c.execute("""
            CREATE TABLE IF NOT EXISTS found_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                source TEXT,
                message_id TEXT,
                title TEXT,
                link TEXT,
                match_score INTEGER,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, source, message_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ===================== کاربران =====================
    
    def save_bio(self, user_id: str, bio: str):
        """ذخیره بیوگرافی"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO users (user_id, bio)
            VALUES (?, ?)
        """, (user_id, bio))
        conn.commit()
        conn.close()
    
    def get_bio(self, user_id: str) -> str:
        """دریافت بیوگرافی"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT bio FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    
    def save_skills(self, user_id: str, skills: List[str]):
        """ذخیره مهارت‌ها"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO users (user_id, skills)
            VALUES (?, ?)
        """, (user_id, json.dumps(skills, ensure_ascii=False)))
        conn.commit()
        conn.close()
    
    def get_skills(self, user_id: str) -> List[str]:
        """دریافت مهارت‌ها"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT skills FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row and row[0] else []
    
    # ===================== کانال‌ها =====================
    
    def add_channel(self, user_id: str, channel: str) -> bool:
        """اضافه کردن کانال"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO user_channels (user_id, channel_username)
                VALUES (?, ?)
            """, (user_id, channel))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_channel(self, user_id: str, channel: str):
        """حذف کانال"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            DELETE FROM user_channels
            WHERE user_id = ? AND channel_username = ?
        """, (user_id, channel))
        conn.commit()
        conn.close()
    
    def get_channels(self, user_id: str) -> List[str]:
        """دریافت لیست کانال‌ها"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT channel_username FROM user_channels
            WHERE user_id = ?
        """, (user_id,))
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]
    
    # ===================== تنظیمات =====================
    
    def set_setting(self, user_id: str, key: str, value):
        """تنظیم مقدار"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO settings (user_id, key, value)
            VALUES (?, ?, ?)
        """, (user_id, key, str(value)))
        conn.commit()
        conn.close()
    
    def get_setting(self, user_id: str, key: str, default=None):
        """دریافت مقدار تنظیم"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT value FROM settings
            WHERE user_id = ? AND key = ?
        """, (user_id, key))
        row = c.fetchone()
        conn.close()
        return row[0] if row else default
    
    # ===================== آمار =====================
    
    def update_stats(self, user_id: str, matches_count: int):
        """به‌روزرسانی آمار"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO stats (user_id, total_scans, total_matches, last_scan)
            VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                total_scans = total_scans + 1,
                total_matches = total_matches + ?,
                last_scan = CURRENT_TIMESTAMP
        """, (user_id, matches_count, matches_count))
        
        conn.commit()
        conn.close()
    
    def get_stats(self, user_id: str) -> Dict:
        """دریافت آمار"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT total_scans, total_matches FROM stats
            WHERE user_id = ?
        """, (user_id,))
        row = c.fetchone()
        conn.close()
        
        return {
            'total_scans': row[0] if row else 0,
            'total_matches': row[1] if row else 0
        }
    
    # ===================== کاربران فعال =====================
    
    def get_all_users(self) -> List[Dict]:
        """دریافت همه کاربران"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        rows = c.fetchall()
        conn.close()
        return [{'user_id': r[0]} for r in rows]
    
    # ===================== پاکسازی =====================
    
    def clear_user_data(self, user_id: str):
        """پاک کردن همه داده‌های کاربر"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM user_channels WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM stats WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
    
    # ===================== شغل‌های یافت شده =====================
    
    def save_found_job(self, user_id: str, job: Dict) -> bool:
        """ذخیره شغل یافت شده (جلوگیری از تکرار)"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO found_jobs (user_id, source, message_id, title, link, match_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                job.get('source', ''),
                job.get('message_id', ''),
                job.get('title', ''),
                job.get('link', ''),
                job.get('match_score', 0)
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def is_job_seen(self, user_id: str, source: str, message_id: str) -> bool:
        """آیا این شغل قبلاً دیده شده؟"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM found_jobs
            WHERE user_id = ? AND source = ? AND message_id = ?
        """, (user_id, source, message_id))
        count = c.fetchone()[0]
        conn.close()
        return count > 0