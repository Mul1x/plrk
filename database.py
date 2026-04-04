import sqlite3
import random
import string
import json
import threading
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "giftguard.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                seller_id INTEGER,
                buyer_id INTEGER,
                deal_type TEXT,
                description TEXT,
                amount REAL,
                currency TEXT DEFAULT 'RUB',
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                secret_code TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                frozen_balance REAL DEFAULT 0,
                seller_deals INTEGER DEFAULT 0,
                buyer_deals INTEGER DEFAULT 0,
                rating REAL DEFAULT 5.0,
                requisites TEXT DEFAULT '{}',
                language TEXT DEFAULT 'ru'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                total_paid REAL DEFAULT 0,
                total_deals INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        """)
        cursor.execute(
            "INSERT OR IGNORE INTO stats (id, total_paid, total_deals) VALUES (1, 0, 0)"
        )
        self.conn.commit()

    def add_admin(self, user_id: int):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
            self.conn.commit()

    def remove_admin(self, user_id: int):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            self.conn.commit()

    def get_admins(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM admins")
        return [row[0] for row in cursor.fetchall()]

    def update_language(self, user_id: int, lang: str):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
            self.conn.commit()

    def get_user_lang(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user[9] if user and len(user) > 9 else 'ru'

    def get_all_users(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

    def get_user(self, user_id: int) -> Optional[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

    def save_user(self, user_id: int, username: str, first_name: str):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name),
            )
            self.conn.commit()

    def update_requisites(self, user_id: int, req_type: str, value: str):
        with self._lock:
            cursor = self.conn.cursor()
            user = self.get_user(user_id)
            requisites = {}
            if user and user[8]:
                try:
                    requisites = json.loads(user[8])
                except:
                    pass
            requisites[req_type] = value
            cursor.execute(
                "UPDATE users SET requisites = ? WHERE user_id = ?",
                (json.dumps(requisites), user_id),
            )
            self.conn.commit()

    def has_requisites(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя хотя бы один реквизит"""
        user = self.get_user(user_id)
        if not user or not user[8]:
            return False
        try:
            requisites = json.loads(user[8])
            for value in requisites.values():
                if value and value != "<i>не указано</i>" and value.strip():
                    return True
            return False
        except:
            return False

    def create_deal(self, seller_id: int, deal_type: str, description: str, amount: float, currency: str) -> str:
        deal_id = "".join(random.choices(string.digits, k=6))
        secret_code = "".join(random.choices(string.digits, k=6))
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO deals (deal_id, seller_id, deal_type, description, amount, currency, secret_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (deal_id, seller_id, deal_type, description, amount, currency, secret_code),
            )
            cursor.execute("UPDATE stats SET total_deals = total_deals + 1 WHERE id = 1")
            self.conn.commit()
        return deal_id

    def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        row = cursor.fetchone()
        if row:
            result = {
                "deal_id": row[0],
                "seller_id": row[1],
                "buyer_id": row[2],
                "deal_type": row[3],
                "description": row[4],
                "amount": row[5],
                "currency": row[6],
                "status": row[7],
                "created_at": row[8],
                "paid_at": row[9],
            }
            if len(row) > 10:
                result["secret_code"] = row[10]
            else:
                result["secret_code"] = None
            return result
        return None

    def set_buyer(self, deal_id: str, buyer_id: int):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE deals SET buyer_id = ? WHERE deal_id = ?", (buyer_id, deal_id)
            )
            self.conn.commit()

    def clear_buyer(self, deal_id: str):
        """Очищает покупателя в сделке (при выходе)"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE deals SET buyer_id = NULL WHERE deal_id = ?", (deal_id,)
            )
            self.conn.commit()

    def mark_paid(self, deal_id: str):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE deals SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE deal_id = ?",
                (deal_id,),
            )
            deal = self.get_deal(deal_id)
            if deal:
                cursor.execute(
                    "UPDATE stats SET total_paid = total_paid + ? WHERE id = 1",
                    (deal["amount"],),
                )
            self.conn.commit()

    def get_user_deals(self, user_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM deals WHERE seller_id = ? OR buyer_id = ? ORDER BY created_at DESC",
            (user_id, user_id),
        )
        return cursor.fetchall()

    def get_stats(self) -> Optional[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stats WHERE id = 1")
        return cursor.fetchone()

    def get_deal_secret_code(self, deal_id: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT secret_code FROM deals WHERE deal_id = ?", (deal_id,))
        row = cursor.fetchone()
        return row[0] if row else None
        # ========== ПОДПИСКИ ==========
    
    def create_subscriptions_table(self):
        """Создает таблицу для подписок (вызови в _init_db)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                plan_type TEXT,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                payment_amount INTEGER,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_subscription(self, user_id: int, plan_type: str, duration_days: int, payment_amount: int):
        """Добавляет или обновляет подписку пользователя"""
        from datetime import datetime, timedelta
        
        with self._lock:
            cursor = self.conn.cursor()
            end_date = datetime.now() + timedelta(days=duration_days)
            
            # Удаляем старую подписку, если есть
            cursor.execute("DELETE FROM user_subscriptions WHERE user_id = ?", (user_id,))
            
            # Добавляем новую
            cursor.execute("""
                INSERT INTO user_subscriptions (user_id, plan_type, end_date, payment_amount, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, plan_type, end_date.isoformat(), payment_amount))
            self.conn.commit()
    
    def get_active_subscription(self, user_id: int) -> Optional[Dict]:
        """Возвращает активную подписку пользователя, если есть"""
        from datetime import datetime
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, plan_type, start_date, end_date, payment_amount, is_active
            FROM user_subscriptions 
            WHERE user_id = ? AND is_active = 1 AND end_date > datetime('now')
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row[0],
                "plan_type": row[1],
                "start_date": row[2],
                "end_date": row[3],
                "payment_amount": row[4],
                "is_active": row[5]
            }
        return None
    
    def is_premium_subscriber(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь активным подписчиком"""
        return self.get_active_subscription(user_id) is not None
    
    def deactivate_expired_subscriptions(self):
        """Деактивирует истекшие подписки"""
        from datetime import datetime
        
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE user_subscriptions 
                SET is_active = 0 
                WHERE is_active = 1 AND end_date <= datetime('now')
            """)
            self.conn.commit()
    
    def get_all_active_subscribers(self) -> list:
        """Возвращает список ID всех активных подписчиков"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id FROM user_subscriptions 
            WHERE is_active = 1 AND end_date > datetime('now')
        """)
        return [row[0] for row in cursor.fetchall()]

db = Database()
