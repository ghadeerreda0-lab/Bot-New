"""
معالجات عمليات الدفع والشحن
"""

import logging
from telebot import TeleBot
from services.user_service import UserService
from services.payment_service import PaymentService
from utils.validators import validate_amount

logger = logging.getLogger(__name__)

def register_payment_handlers(bot: TeleBot, user_service: UserService,
                            payment_service: PaymentService):
    """تسجيل معالجات عمليات الدفع"""
    
    # Note: هذه الدوال تحتاج إلى نظام جلسات لإكمالها
    # سيتم إكمالها بعد إنشاء نظام الجلسات
    
    logger.info("✅ تم تسجيل معالجات الدفع (جاهز للتكامل مع الجلسات)")