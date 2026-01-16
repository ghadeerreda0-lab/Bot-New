#!/usr/bin/env python3
"""
البوت الاحترافي - الإصدار 6.0.0
نظام متكامل لإدارة الشحن والسحب والإحالات
"""

import logging
import sys
import os
from telebot import TeleBot
from apscheduler.schedulers.background import BackgroundScheduler

# إضافة المسارات للملفات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# استيراد المكونات
from config import TOKEN, setup_logging
from database.db_manager import DatabaseManager
from services.user_service import UserService
from services.payment_service import PaymentService
from services.ichancy_service import IchancyService
from handlers import register_all_handlers

# إعداد التسجيل
logger = setup_logging()

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    print("=" * 70)
    print("🤖 **البوت الاحترافي - الإصدار 6.0.0**")
    print("=" * 70)
    
    try:
        # إنشاء البوت
        bot = TeleBot(TOKEN)
        logger.info("✅ تم إنشاء كائن البوت")
        
        # تهيئة قاعدة البيانات
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        logger.info("✅ تم تهيئة قاعدة البيانات")
        
        # تهيئة الخدمات
        user_service = UserService(db_manager)
        payment_service = PaymentService(db_manager)
        ichancy_service = IchancyService(db_manager)
        
        # تسجيل جميع المعالجات
        register_all_handlers(bot, user_service, payment_service, ichancy_service)
        logger.info("✅ تم تسجيل جميع المعالجات")
        
        # بدء نظام الجدولة
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("✅ تم بدء نظام الجدولة")
        
        # عرض معلومات النظام
        print(f"👑 الإدمن الرئيسي: 8146077656")
        print(f"🔄 الإصدار: 6.0.0")
        print(f"📅 آخر تحديث: 2024-01-16")
        print("=" * 70)
        print("✅ **نظام التشغيل:**")
        print("   📱 سيرياتيل كاش: ✅")
        print("   💰 شام كاش: ✅")
        print("   💵 شام كاش دولار: ✅")
        print("   ⚡ Ichancy: ✅")
        print("   💸 السحب: ✅")
        print("=" * 70)
        print("🚀 **البوت يعمل وجاهز للاستخدام!**")
        print("=" * 70)
        
        # بدء الاستماع للرسائل
        bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        
    except Exception as e:
        logger.critical(f"🚨 فشل تشغيل البوت: {e}", exc_info=True)
        print(f"❌ فشل تشغيل البوت: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()