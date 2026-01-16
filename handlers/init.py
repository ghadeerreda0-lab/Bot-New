"""
حزمة معالجات البوت - ملف التجميع
"""

import logging
from telebot import TeleBot
from services.user_service import UserService
from services.payment_service import PaymentService
from services.ichancy_service import IchancyService
from services.referral_service import ReferralService
from services.gift_service import GiftService
from services.transaction_service import TransactionService

from .user_handlers import register_user_handlers
from .admin_handlers import register_admin_handlers
from .payment_handlers import register_payment_handlers
from .callback_handlers import register_callback_handlers

logger = logging.getLogger(__name__)

def register_all_handlers(bot: TeleBot, user_service: UserService,
                         payment_service: PaymentService,
                         ichancy_service: IchancyService,
                         referral_service: ReferralService,
                         gift_service: GiftService,
                         transaction_service: TransactionService):
    """تسجيل جميع المعالجات"""
    
    try:
        # تسجيل معالجات المستخدمين
        register_user_handlers(bot, user_service, payment_service, 
                              ichancy_service, referral_service, gift_service)
        
        # تسجيل معالجات الأدمن
        register_admin_handlers(bot, user_service, payment_service,
                               ichancy_service, referral_service,
                               gift_service, transaction_service)
        
        # تسجيل معالجات الكال باك
        register_callback_handlers(bot, user_service, payment_service,
                                  transaction_service, gift_service)
        
        # تسجيل معالجات الدفع (جاهزة للتكامل)
        register_payment_handlers(bot, user_service, payment_service)
        
        logger.info("✅ تم تسجيل جميع المعالجات بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل تسجيل المعالجات: {e}")
        return False