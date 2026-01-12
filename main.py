import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import random

from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telebot import types

import asyncpg
import aioredis
from cachetools import TTLCache
from flask import Flask
from threading import Thread

# =========================
# Flask للحفاظ على البوت نشط
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "IChancy Bot is running on Render!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# =========================
# إعدادات التسجيل
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# إعدادات التكوين لـ Render
# =========================
class Config:
    # Render يوفر هذه المتغيرات تلقائياً
    TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    
    # القنوات - يمكن تعديلها من Render
    CHANNEL_SYR_CASH = int(os.getenv("CHANNEL_SYR_CASH", "-1003597919374"))
    CHANNEL_SCH_CASH = int(os.getenv("CHANNEL_SCH_CASH", "-1003464319533"))
    CHANNEL_ADMIN_LOGS = int(os.getenv("CHANNEL_ADMIN_LOGS", "-1003577468648"))
    CHANNEL_WITHDRAW = int(os.getenv("CHANNEL_WITHDRAW", "-1003443113179"))
    CHANNEL_SUPPORT = int(os.getenv("CHANNEL_SUPPORT", "-1003514396473"))
    
    # قاعدة البيانات - Render يضيفها تلقائياً
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # حدود الأمان
    MAX_WITHDRAW_PER_DAY = 5000000
    MIN_TRANSACTION = 1000
    MAX_TRANSACTION = 10000000
    
config = Config()
bot = AsyncTeleBot(config.TOKEN)

# =========================
# إدارة الاتصالات
# =========================
class ConnectionManager:
    _db_pool = None
    _redis = None
    
    @classmethod
    async def init_db(cls):
        """تهيئة PostgreSQL"""
        if not cls._db_pool and config.DATABASE_URL:
            try:
                cls._db_pool = await asyncpg.create_pool(
                    config.DATABASE_URL,
                    min_size=2,
                    max_size=5,
                    command_timeout=30
                )
                await cls._create_tables()
                logger.info("✅ PostgreSQL جاهز")
            except Exception as e:
                logger.error(f"❌ خطأ في PostgreSQL: {e}")
                cls._db_pool = None
    
    @classmethod
    async def init_redis(cls):
        """تهيئة Redis"""
        if not cls._redis and config.REDIS_URL:
            try:
                cls._redis = await aioredis.from_url(
                    config.REDIS_URL,
                    decode_responses=True,
                    max_connections=5
                )
                logger.info("✅ Redis جاهز")
            except Exception as e:
                logger.error(f"❌ خطأ في Redis: {e}")
                cls._redis = None
    
    @classmethod
    async def _create_tables(cls):
        """إنشاء جداول متوافقة مع Render"""
        async with cls._db_pool.acquire() as conn:
            # جدول المستخدمين
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance BIGINT DEFAULT 0 CHECK (balance >= 0),
                total_deposited BIGINT DEFAULT 0,
                total_withdrawn BIGINT DEFAULT 0,
                last_transaction TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # جدول المعاملات (بدون partitioning)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                type VARCHAR(20) NOT NULL CHECK (type IN ('deposit', 'withdraw')),
                amount BIGINT NOT NULL CHECK (amount > 0),
                payment_method VARCHAR(50) NOT NULL,
                transaction_id VARCHAR(100),
                account_number VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed')),
                monthly_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # فهارس أساسية
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_status 
            ON transactions(user_id, status)
            """)
            
            await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_created 
            ON transactions(created_at DESC)
            """)
            
            # جدول العداد الشهري
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS monthly_counter (
                month INTEGER,
                year INTEGER,
                payment_method VARCHAR(50),
                counter INTEGER DEFAULT 0,
                PRIMARY KEY (month, year, payment_method)
            )
            """)
            
            # جدول رسائل الدعم
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username VARCHAR(100),
                message TEXT NOT NULL,
                admin_reply TEXT,
                status VARCHAR(20) DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP
            )
            """)
            
            # جدول سجل الأمان
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                action VARCHAR(100) NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            logger.info("✅ الجداول جاهزة")

# =========================
# إدارة التخزين المؤقت
# =========================
class CacheManager:
    def __init__(self):
        self.local_cache = TTLCache(maxsize=500, ttl=60)
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """الحصول على بيانات المستخدم"""
        if user_id in self.local_cache:
            return self.local_cache[user_id]
        
        if ConnectionManager._redis:
            cached = await ConnectionManager._redis.get(f"user:{user_id}")
            if cached:
                user_data = json.loads(cached)
                self.local_cache[user_id] = user_data
                return user_data
        
        if ConnectionManager._db_pool:
            async with ConnectionManager._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id, balance FROM users WHERE user_id = $1",
                    user_id
                )
                if row:
                    user_data = dict(row)
                    if ConnectionManager._redis:
                        await ConnectionManager._redis.setex(
                            f"user:{user_id}", 300, json.dumps(user_data)
                        )
                    self.local_cache[user_id] = user_data
                    return user_data
        
        return None
    
    async def set_user_cache(self, user_id: int, user_data: Dict):
        """تحديث تخزين المستخدم"""
        self.local_cache[user_id] = user_data
        if ConnectionManager._redis:
            await ConnectionManager._redis.setex(
                f"user:{user_id}", 300, json.dumps(user_data)
            )

# =========================
# إدارة المستخدمين
# =========================
class UserManager:
    def __init__(self):
        self.cache = CacheManager()
    
    async def get_or_create_user(self, user_id: int) -> Dict:
        """الحصول على مستخدم أو إنشاءه"""
        user = await self.cache.get_user(user_id)
        if user:
            return user
        
        if ConnectionManager._db_pool:
            async with ConnectionManager._db_pool.acquire() as conn:
                try:
                    await conn.execute("""
                    INSERT INTO users (user_id, balance)
                    VALUES ($1, 0)
                    ON CONFLICT (user_id) DO NOTHING
                    """, user_id)
                    
                    row = await conn.fetchrow(
                        "SELECT user_id, balance FROM users WHERE user_id = $1",
                        user_id
                    )
                    
                    if row:
                        user_data = dict(row)
                        await self.cache.set_user_cache(user_id, user_data)
                        return user_data
                except Exception as e:
                    logger.error(f"خطأ في إنشاء المستخدم: {e}")
        
        return {"user_id": user_id, "balance": 0}
    
    async def add_balance(self, user_id: int, amount: int):
        """إضافة رصيد"""
        if ConnectionManager._db_pool:
            try:
                async with ConnectionManager._db_pool.acquire() as conn:
                    result = await conn.fetchrow("""
                    UPDATE users 
                    SET balance = balance + $2,
                        total_deposited = total_deposited + $2,
                        last_transaction = CURRENT_TIMESTAMP
                    WHERE user_id = $1
                    RETURNING balance
                    """, user_id, amount)
                    
                    if result:
                        await self.cache.set_user_cache(user_id, {"user_id": user_id, "balance": result["balance"]})
                        return result["balance"]
            except Exception as e:
                logger.error(f"خطأ في إضافة الرصيد: {e}")
        
        return None

# =========================
# إدارة الجلسات
# =========================
class SessionManager:
    @staticmethod
    async def set_session(user_id: int, step: str, data: Dict = None):
        """تعيين جلسة"""
        if ConnectionManager._redis:
            session_data = {
                "step": step,
                "data": data or {},
                "created": datetime.now().isoformat()
            }
            await ConnectionManager._redis.setex(
                f"session:{user_id}", 3600, json.dumps(session_data)
            )
            return True
        return False
    
    @staticmethod
    async def get_session(user_id: int) -> Optional[Dict]:
        """الحصول على جلسة"""
        if ConnectionManager._redis:
            data = await ConnectionManager._redis.get(f"session:{user_id}")
            if data:
                return json.loads(data)
        return None
    
    @staticmethod
    async def clear_session(user_id: int):
        """مسح جلسة"""
        if ConnectionManager._redis:
            await ConnectionManager._redis.delete(f"session:{user_id}")

# =========================
# تهيئة المديرين
# =========================
connection_manager = ConnectionManager()
user_manager = UserManager()
session_manager = SessionManager()

async def init_services():
    """تهيئة الخدمات"""
    await connection_manager.init_db()
    await connection_manager.init_redis()

# =========================
# القائمة الرئيسية (نفس الواجهة)
# =========================
def main_menu(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⚡ Ichancy", callback_data="ichancy"))
    kb.add(
        InlineKeyboardButton("📥 شحن رصيد", callback_data="charge"),
        InlineKeyboardButton("📤 سحب رصيد", callback_data="withdraw")
    )
    kb.add(InlineKeyboardButton("💰 نظام الاحالات", callback_data="referrals"))
    kb.add(
        InlineKeyboardButton("🎁 اهداء رصيد", callback_data="gift"),
        InlineKeyboardButton("🎁 كود هدية", callback_data="gift_code")
    )
    kb.add(
        InlineKeyboardButton("✉️ تواصل مع الدعم", callback_data="support"),
        InlineKeyboardButton("✉️ تواصل معنا", callback_data="contact")
    )
    kb.add(
        InlineKeyboardButton("🔁 السجل", callback_data="logs"),
        InlineKeyboardButton("☁️ الشروحات", callback_data="tutorials")
    )
    kb.add(InlineKeyboardButton("🔁 سجل الرهانات", callback_data="bets"))
    kb.add(InlineKeyboardButton("🆕 🃏 الجاكبوت", callback_data="jackpot"))
    kb.add(
        InlineKeyboardButton("↗️ Vp لتشغيل كامل اقسام الموقع", callback_data="vp"),
        InlineKeyboardButton("↗️ ichancy apk", callback_data="apk")
    )
    kb.add(InlineKeyboardButton("📌 الشروط والأحكام", callback_data="rules"))
    
    if user_id == config.ADMIN_ID:
        kb.add(InlineKeyboardButton("🎛 لوحة التحكم", callback_data="admin_panel"))
    
    return kb

# =========================
# معالجات البوت
# =========================
@bot.message_handler(commands=["start"])
async def start_command(message: types.Message):
    try:
        uid = message.from_user.id
        
        await init_services()
        user = await user_manager.get_or_create_user(uid)
        balance = user.get("balance", 0)
        
        await bot.send_message(
            message.chat.id,
            f"👋 أهلاً بك!\nرصيدك الحالي: {balance} ليرة سورية",
            reply_markup=main_menu(uid)
        )
        
        await session_manager.clear_session(uid)
        
        if ConnectionManager._db_pool:
            async with ConnectionManager._db_pool.acquire() as conn:
                await conn.execute("""
                INSERT INTO security_logs (user_id, action, details)
                VALUES ($1, $2, $3)
                """, uid, "start", json.dumps({
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name
                }))
                
    except Exception as e:
        logger.error(f"خطأ في start: {e}")
        await bot.send_message(
            message.chat.id,
            "⚠️ مرحباً! البوت يعمل ولكن قاعدة البيانات قيد الإعداد."
        )

@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call: CallbackQuery):
    try:
        uid = call.from_user.id
        data = call.data
        
        if data == "support":
            await session_manager.set_session(uid, "support")
            await bot.send_message(call.message.chat.id, "✍️ اكتب رسالتك للدعم:")
            await bot.answer_callback_query(call.id)
        
        elif data == "charge":
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("💰 سيرياتيل كاش", callback_data="pay_syr"),
                InlineKeyboardButton("💰 شام كاش", callback_data="pay_sch")
            )
            kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data="back"))
            await bot.send_message(call.message.chat.id, "📥 اختر طريقة الدفع:", reply_markup=kb)
            await session_manager.set_session(uid, "awaiting_payment")
            await bot.answer_callback_query(call.id)
        
        elif data == "withdraw":
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("💰 سيرياتيل كاش", callback_data="withdraw_syr"),
                InlineKeyboardButton("💰 شام كاش", callback_data="withdraw_sch")
            )
            kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data="back"))
            await bot.send_message(call.message.chat.id, "📤 اختر طريقة السحب:", reply_markup=kb)
            await session_manager.set_session(uid, "awaiting_withdraw")
            await bot.answer_callback_query(call.id)
        
        elif data in ["pay_syr", "pay_sch"]:
            payment = "سيرياتيل كاش" if data == "pay_syr" else "شام كاش"
            number = "099XXXXXXXX" if data == "pay_syr" else "094YYYYYYYY"
            await session_manager.set_session(uid, "awaiting_amount", {
                "payment": payment,
                "number": number,
                "type": "deposit"
            })
            await bot.send_message(
                call.message.chat.id,
                f"💳 حول المبلغ على الرقم: {number}\n💵 بعد التحويل، أدخل المبلغ:"
            )
            await bot.answer_callback_query(call.id)
        
        elif data == "back":
            await bot.send_message(
                call.message.chat.id,
                "✅ عدنا إلى القائمة الرئيسية:",
                reply_markup=main_menu(uid)
            )
            await session_manager.clear_session(uid)
            await bot.answer_callback_query(call.id)
        
        elif data in ["withdraw_syr", "withdraw_sch"]:
            payment = "سيرياتيل كاش" if data == "withdraw_syr" else "شام كاش"
            await session_manager.set_session(uid, "awaiting_withdraw_amount", {
                "payment": payment,
                "type": "withdraw"
            })
            await bot.send_message(
                call.message.chat.id,
                f"💵 أدخل المبلغ المراد سحبه عبر {payment}:"
            )
            await bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"خطأ في callback: {e}")
        await bot.answer_callback_query(call.id, "⚠️ حدث خطأ")

@bot.message_handler(func=lambda m: True)
async def message_handler(message: types.Message):
    try:
        uid = message.from_user.id
        session = await session_manager.get_session(uid)
        
        if not session:
            return
        
        step = session.get("step")
        data = session.get("data", {})
        
        if step == "support":
            await bot.send_message(
                message.chat.id,
                "✅ تم إرسال رسالتك للدعم. سنرد عليك قريباً."
            )
            await session_manager.clear_session(uid)
        
        elif step == "awaiting_amount":
            if message.text.isdigit():
                amount = int(message.text)
                if amount > 0:
                    await bot.send_message(
                        message.chat.id,
                        f"✅ تم استلام طلبك بمبلغ {amount} ليرة.\n"
                        f"🔑 أرسل رقم العملية (Transaction ID):"
                    )
                    data["amount"] = amount
                    await session_manager.set_session(uid, "awaiting_txid", data)
                else:
                    await bot.send_message(message.chat.id, "❌ المبلغ يجب أن يكون موجباً")
        
        elif step == "awaiting_txid":
            txid = message.text.strip()
            if len(txid) >= 3:
                amount = data.get("amount", 0)
                payment = data.get("payment", "")
                
                if ConnectionManager._db_pool:
                    async with ConnectionManager._db_pool.acquire() as conn:
                        await conn.execute("""
                        INSERT INTO transactions 
                        (user_id, type, amount, payment_method, transaction_id, status)
                        VALUES ($1, $2, $3, $4, $5, 'pending')
                        """, uid, "deposit", amount, payment, txid)
                
                await bot.send_message(
                    message.chat.id,
                    "✅ تم إرسال طلبك للمراجعة. سيتم تفعيله بعد الموافقة."
                )
                await session_manager.clear_session(uid)
        
        elif step == "awaiting_withdraw_amount":
            if message.text.isdigit():
                amount = int(message.text)
                user = await user_manager.get_or_create_user(uid)
                
                if amount <= user.get("balance", 0):
                    await bot.send_message(
                        message.chat.id,
                        "💳 الآن أدخل رقم الحساب لاستلام المبلغ:"
                    )
                    data["amount"] = amount
                    await session_manager.set_session(uid, "awaiting_account", data)
                else:
                    await bot.send_message(
                        message.chat.id,
                        f"❌ رصيدك غير كافي. رصيدك: {user.get('balance', 0)}"
                    )
        
        elif step == "awaiting_account":
            account = message.text.strip()
            if len(account) >= 3:
                amount = data.get("amount", 0)
                payment = data.get("payment", "")
                
                if ConnectionManager._db_pool:
                    async with ConnectionManager._db_pool.acquire() as conn:
                        txid = str(random.randint(10000, 99999))
                        await conn.execute("""
                        INSERT INTO transactions 
                        (user_id, type, amount, payment_method, transaction_id, account_number, status)
                        VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                        """, uid, "withdraw", amount, payment, txid, account)
                
                await bot.send_message(
                    message.chat.id,
                    "✅ تم إرسال طلب السحب للمراجعة. سيتم تفعيله بعد الموافقة."
                )
                await session_manager.clear_session(uid)
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {e}")

# =========================
# التشغيل الرئيسي
# =========================
async def main():
    keep_alive()  # إبقاء البوت نشط
    
    print("=" * 50)
    print("🚀 بدء تشغيل IChancy Bot على Render")
    print("=" * 50)
    
    try:
        await init_services()
        print("✅ جميع الخدمات جاهزة")
        print(f"🤖 البوت: @{(await bot.get_me()).username}")
        print("📱 اكتب /start في تيليجرام")
        print("=" * 50)
        
        await bot.polling(none_stop=True, timeout=30)
        
    except Exception as e:
        print(f"❌ خطأ رئيسي: {e}")
    finally:
        if ConnectionManager._db_pool:
            await ConnectionManager._db_pool.close()
        if ConnectionManager._redis:
            await ConnectionManager._redis.close()

if __name__ == "__main__":
    asyncio.run(main())
