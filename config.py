"""
إعدادات وتكوين النظام
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعدادات البوت - التوكن كما هو
TOKEN = os.getenv("TOKEN", "8563127617:AAEqQh1bWM8k2gMFqmAWLUJvWTK3rFyp4k8")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8146077656"))
DB_PATH = os.getenv("DB_PATH", "bot_database.sqlite")
LOG_FILE = "bot_logs.log"

# القنوات (كما في الكود الأصلي)
CHANNEL_SYR_CASH = -1003597919374
CHANNEL_SCH_CASH = -1003464319533
CHANNEL_ADMIN_LOGS = -1003577468648
CHANNEL_WITHDRAW = -1003443113179
CHANNEL_SUPPORT = -1003514396473
CHANNEL_ERROR_LOGS = -1003661244115
CHANNEL_DAILY_STATS = -1003478157091
CHANNEL_DB_BACKUP = -1003612263016
CHANNEL_URGENT_REQUESTS = -1003577468648

# ثوابت النظام
MAX_CODES = 20
CODE_CAPACITY = 5400
MAX_ADMINS = 10
REFERRAL_CODE_LENGTH = 8
VERSION = "6.0.0"
LAST_UPDATE = "2024-01-16"

def setup_logging():
    """إعداد نظام التسجيل"""
    
    # إنشاء مجلد السجلات إذا لم يكن موجوداً
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # تكوين التسجيل
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                f"logs/{LOG_FILE}",
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# إعدادات الدفع
PAYMENT_METHODS = {
    'syriatel_cash': {
        'name': '📱 سيرياتيل كاش',
        'channel': CHANNEL_SYR_CASH,
        'min_amount': 1000,
        'max_amount': 50000
    },
    'sham_cash': {
        'name': '💰 شام كاش', 
        'channel': CHANNEL_SCH_CASH,
        'min_amount': 1000,
        'max_amount': 50000
    },
    'sham_cash_usd': {
        'name': '💵 شام كاش دولار',
        'channel': CHANNEL_SCH_CASH,
        'min_amount': 10,
        'max_amount': 500
    }
}