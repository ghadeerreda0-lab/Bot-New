"""
إعدادات النظام الأساسية
"""
import os
import logging
from datetime import timedelta
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

class Config:
    # ========== TELEGRAM ==========
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # ========== DATABASE ==========
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ichancy_bot")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # ========== WEBHOOKS ==========
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://yourdomain.com")
    WEBHOOK_PATH = f"/bot/{BOT_TOKEN}"
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    ICHANCY_API_URL = os.getenv("ICHANCY_API_URL", "https://agents.ichancy.com/api")
    ICHANCY_USERNAME = os.getenv("ICHANCY_USERNAME")
    ICHANCY_PASSWORD = os.getenv("ICHANCY_PASSWORD")
    
    # ========== PAYMENT SETTINGS ==========
    SYRIATEL_CASH_CODES = {}  # سيتم تعبئته من قاعدة البيانات
    CHAM_CASH_SETTINGS = {}
    MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "500.0"))
    MAX_DEPOSIT = float(os.getenv("MAX_DEPOSIT", "50000.0"))
    WITHDRAWAL_FEE = float(os.getenv("WITHDRAWAL_FEE", "10.0"))  # نسبة مئوية
    
    # ========== REFERRAL SYSTEM ==========
    REFERRAL_BONUS_PERCENT = float(os.getenv("REFERRAL_BONUS_PERCENT", "5.0"))
    MIN_ACTIVE_REFERRALS = int(os.getenv("MIN_ACTIVE_REFERRALS", "5"))
    MIN_BURN_AMOUNT = float(os.getenv("MIN_BURN_AMOUNT", "250.0"))
    
    # ========== CHANNELS ==========
    LOG_CHANNEL = os.getenv("LOG_CHANNEL", "@ichancy_logs")
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@ichancy_support")
    TRANSACTION_CHANNEL = os.getenv("TRANSACTION_CHANNEL", "@ichancy_transactions")
    REPORT_CHANNEL = os.getenv("REPORT_CHANNEL", "@ichancy_reports")
    
    # ========== SECURITY ==========
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "your-32-char-encryption-key-here")
    JWT_SECRET = os.getenv("JWT_SECRET", "your-jwt-secret-key")
    ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",")
    
    # ========== PERFORMANCE ==========
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 دقائق
    MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "100"))
    
    # ========== TIMING ==========
    REPORT_TIME = "00:00"  # منتصف الليل
    BURN_CHECK_INTERVAL = timedelta(hours=6)
    BONUS_EXPIRY_DAYS = int(os.getenv("BONUS_EXPIRY_DAYS", "30"))

# تكوين التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)