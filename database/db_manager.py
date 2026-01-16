"""
مدير قاعدة البيانات مع جميع الوظائف الأساسية
"""

import sqlite3
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class DatabaseManager:
    """فئة إدارة قاعدة البيانات مع Connection Pooling"""
    
    def __init__(self, db_path: str = "bot_database.sqlite"):
        self.db_path = db_path
        self._lock = Lock()
        self._initialize_connection_pool()
        self._setup_tables()
    
    def _initialize_connection_pool(self):
        """تهيئة Connection Pool"""
        self._connections = []
        self._max_connections = 5
    
    def get_connection(self):
        """الحصول على اتصال من الـ Pool"""
        with self._lock:
            if len(self._connections) < self._max_connections:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                self._connections.append(conn)
                return conn
            else:
                # استخدام اتصال موجود
                return self._connections[0]
    
    def _setup_tables(self):
        """إنشاء جميع الجداول المطلوبة"""
        tables_sql = [
            # جدول المستخدمين
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0 CHECK(balance >= 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                is_banned BOOLEAN DEFAULT 0,
                ban_reason TEXT,
                ban_until TEXT
            )
            """,
            
            # جدول المعاملات
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('charge', 'withdraw', 'gift_sent', 'gift_received', 'referral', 'bonus')),
                amount INTEGER NOT NULL CHECK(amount > 0),
                payment_method TEXT,
                transaction_id TEXT,
                account_number TEXT,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول أكواد سيرياتيل
            """
            CREATE TABLE IF NOT EXISTS syriatel_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_number TEXT NOT NULL UNIQUE,
                current_amount INTEGER DEFAULT 0 CHECK(current_amount >= 0 AND current_amount <= 5400),
                is_active BOOLEAN DEFAULT 1,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT,
                usage_count INTEGER DEFAULT 0
            )
            """,
            
            # جدول سجلات تعبئة الأكواد
            """
            CREATE TABLE IF NOT EXISTS code_fill_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL CHECK(amount > 0),
                remaining_in_code INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code_id) REFERENCES syriatel_codes (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول حسابات Ichancy
            """
            CREATE TABLE IF NOT EXISTS ichancy_accounts (
                user_id INTEGER PRIMARY KEY,
                ichancy_username TEXT UNIQUE NOT NULL,
                ichancy_password TEXT NOT NULL,
                ichancy_balance INTEGER DEFAULT 0 CHECK(ichancy_balance >= 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول الأدمن
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER NOT NULL,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                permissions TEXT DEFAULT 'limited',
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (added_by) REFERENCES users (user_id)
            )
            """,
            
            # جدول الإحالات
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                amount_charged INTEGER DEFAULT 0,
                commission_earned INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id),
                UNIQUE(referred_id)
            )
            """,
            
            # جدول إعدادات الإحالات
            """
            CREATE TABLE IF NOT EXISTS referral_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commission_rate INTEGER DEFAULT 10,
                bonus_amount INTEGER DEFAULT 2000,
                min_active_referrals INTEGER DEFAULT 5,
                min_charge_amount INTEGER DEFAULT 100000,
                next_distribution TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # جدول أكواد الهدايا
            """
            CREATE TABLE IF NOT EXISTS gift_codes (
                code TEXT PRIMARY KEY,
                amount INTEGER NOT NULL CHECK(amount > 0),
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            )
            """,
            
            # جدول استخدام أكواد الهدايا
            """
            CREATE TABLE IF NOT EXISTS gift_code_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code) REFERENCES gift_codes (code),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول عمليات الإهداء
            """
            CREATE TABLE IF NOT EXISTS gift_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                original_amount INTEGER NOT NULL,
                net_amount INTEGER NOT NULL,
                gift_percentage INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (user_id),
                FOREIGN KEY (receiver_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول الجلسات
            """
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                step TEXT NOT NULL,
                temp_data TEXT,
                expires_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """,
            
            # جدول إعدادات النظام
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER
            )
            """,
            
            # جدول الإحصائيات اليومية
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_users INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_deposit INTEGER DEFAULT 0,
                total_withdraw INTEGER DEFAULT 0,
                pending_transactions INTEGER DEFAULT 0,
                support_tickets INTEGER DEFAULT 0,
                resolved_tickets INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0,
                system_errors INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for sql in tables_sql:
                cursor.execute(sql)
            
            # إنشاء الفهارس
            indices = [
                ("idx_transactions_user", "transactions(user_id)"),
                ("idx_transactions_status", "transactions(status)"),
                ("idx_transactions_created", "transactions(created_at)"),
                ("idx_sessions_user", "sessions(user_id)"),
                ("idx_codes_active", "syriatel_codes(is_active)"),
                ("idx_codes_amount", "syriatel_codes(current_amount)"),
                ("idx_referrals_referrer", "referrals(referrer_id)"),
                ("idx_referrals_referred", "referrals(referred_id)"),
                ("idx_gift_codes_expires", "gift_codes(expires_at)"),
                ("idx_gift_code_usage", "gift_code_usage(code, user_id)"),
                ("idx_admins_added", "admins(added_at)"),
                ("idx_users_banned", "users(is_banned)")
            ]
            
            for idx_name, idx_sql in indices:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_sql}")
                except Exception as e:
                    logger.warning(f"فشل إنشاء فهرس {idx_name}: {e}")
            
            conn.commit()
            logger.info("✅ تم إنشاء جميع الجداول والفهارس")
            
            # تهيئة الإعدادات الافتراضية
            self._initialize_default_settings(cursor)
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الجداول: {e}")
            raise
    
    def _initialize_default_settings(self, cursor):
        """تهيئة الإعدادات الافتراضية"""
        default_settings = [
            ('maintenance_mode', 'false', 'وضع الصيانة'),
            ('maintenance_message', '🔧 البوت تحت الصيانة حاليًا. الرجاء المحاولة لاحقًا.', 'رسالة الصيانة'),
            ('welcome_message', '👋 أهلاً بك!\nرصيدك الحالي: {balance} ليرة سورية', 'رسالة الترحيب'),
            ('contact_info', '📞 للاستفسار: @username', 'معلومات التواصل'),
            ('auto_backup', 'true', 'النسخ الاحتياطي التلقائي'),
            ('backup_interval_hours', '6', 'فترة النسخ الاحتياطي'),
            ('daily_report_time', '23:59', 'وقت التقرير اليومي'),
            ('enable_error_notifications', 'true', 'إشعارات الأخطاء'),
            ('ichancy_enabled', 'true', 'تفعيل Ichancy'),
            ('ichancy_create_account_enabled', 'true', 'تفعيل إنشاء حساب Ichancy'),
            ('ichancy_deposit_enabled', 'true', 'تفعيل شحن Ichancy'),
            ('ichancy_withdraw_enabled', 'true', 'تفعيل سحب Ichancy'),
            ('ichancy_welcome_message', '⚡ مرحباً بك في نظام Ichancy!', 'رسالة Ichancy'),
            ('deposit_enabled', 'true', 'تفعيل الشحن'),
            ('deposit_message', '💰 نظام الشحن مفعل حالياً', 'رسالة الشحن'),
            ('withdraw_enabled', 'true', 'تفعيل السحب'),
            ('withdraw_message', '💸 نظام السحب مفعل حالياً', 'رسالة السحب'),
            ('withdraw_percentage', '0', 'نسبة السحب'),
            ('withdraw_button_visible', 'true', 'إظهار زر السحب'),
            ('gift_percentage', '0', 'نسبة الإهداء'),
            ('max_admins', '10', 'الحد الأقصى للأدمن'),
            ('syriatel_cash_enabled', 'true', 'تفعيل سيرياتيل كاش'),
            ('sham_cash_enabled', 'true', 'تفعيل شام كاش'),
            ('sham_cash_usd_enabled', 'true', 'تفعيل شام كاش دولار'),
            ('syriatel_cash_visible', 'true', 'إظهار سيرياتيل كاش'),
            ('sham_cash_visible', 'true', 'إظهار شام كاش'),
            ('sham_cash_usd_visible', 'true', 'إظهار شام كاش دولار')
        ]
        
        for key, value, description in default_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO system_settings (key, value, updated_by) 
                VALUES (?, ?, ?)
            """, (key, value, 8146077656))
        
        # إعدادات الحدود الافتراضية
        payment_limits = [
            ('syriatel_cash', 1000, 50000),
            ('sham_cash', 1000, 50000),
            ('sham_cash_usd', 10, 500)
        ]
        
        for method, min_amount, max_amount in payment_limits:
            cursor.execute("""
                INSERT OR IGNORE INTO payment_settings 
                (payment_method, is_visible, is_active, pause_message, min_amount, max_amount)
                VALUES (?, 1, 1, ?, ?, ?)
            """, (method, f'⏸️ خدمة {method} متوقفة مؤقتاً', min_amount, max_amount))
        
        # إعدادات الإحالات الافتراضية
        cursor.execute("""
            INSERT OR IGNORE INTO referral_settings 
            (commission_rate, bonus_amount, min_active_referrals, min_charge_amount, next_distribution)
            VALUES (10, 2000, 5, 100000, '2024-01-31 23:59:59')
        """)
        
        logger.info("✅ تم تهيئة الإعدادات الافتراضية")
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        """تنفيذ استعلام مع معاملات"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.lastrowid
            
            conn.commit()
            return result
        except Exception as e:
            logger.error(f"❌ خطأ في تنفيذ الاستعلام: {e}")
            conn.rollback()
            raise
    
    def close_all_connections(self):
        """إغلاق جميع الاتصالات"""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except:
                    pass
            self._connections.clear()
    
    def __del__(self):
        """التدمير وإغلاق الاتصالات"""
        self.close_all_connections()