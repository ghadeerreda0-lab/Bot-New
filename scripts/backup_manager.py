"""
مدير النسخ الاحتياطي والتقارير
"""
import logging
import asyncio
import json
import gzip
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from pathlib import Path

from sqlalchemy.orm import Session
from telegram import Bot
import pandas as pd

from database.models import SessionLocal, User, Transaction, SystemLog
from config import Config
from utils.security import SecurityUtils

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    async def create_database_backup(self) -> Optional[str]:
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"db_backup_{timestamp}.json.gz"
            
            db = SessionLocal()
            try:
                # جمع البيانات
                backup_data = {
                    "metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "total_users": 0,
                        "total_transactions": 0
                    },
                    "users": [],
                    "transactions": [],
                    "system_logs": []
                }
                
                # نسخ المستخدمين (بدون بيانات حساسة)
                users = db.query(User).limit(10000).all()
                backup_data["metadata"]["total_users"] = len(users)
                
                for user in users:
                    backup_data["users"].append({
                        "id": user.id,
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "balance": user.balance,
                        "referral_code": user.referral_code,
                        "is_active": user.is_active,
                        "is_banned": user.is_banned,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "updated_at": user.updated_at.isoformat() if user.updated_at else None
                    })
                
                # نسخ المعاملات (آخر 50000 معاملة)
                transactions = db.query(Transaction).order_by(
                    Transaction.created_at.desc()
                ).limit(50000).all()
                
                backup_data["metadata"]["total_transactions"] = len(transactions)
                
                for trans in transactions:
                    backup_data["transactions"].append({
                        "id": trans.id,
                        "user_id": trans.user_id,
                        "transaction_type": trans.transaction_type,
                        "amount": trans.amount,
                        "fee": trans.fee,
                        "net_amount": trans.net_amount,
                        "payment_method": trans.payment_method,
                        "transaction_code": trans.transaction_code,
                        "status": trans.status,
                        "admin_id": trans.admin_id,
                        "auto_verified": trans.auto_verified,
                        "notes": trans.notes,
                        "created_at": trans.created_at.isoformat() if trans.created_at else None,
                        "completed_at": trans.completed_at.isoformat() if trans.completed_at else None
                    })
                
                # نسخ سجلات النظام (آخر 10000 سجل)
                logs = db.query(SystemLog).order_by(
                    SystemLog.created_at.desc()
                ).limit(10000).all()
                
                for log in logs:
                    backup_data["system_logs"].append({
                        "id": log.id,
                        "log_level": log.log_level,
                        "module": log.module,
                        "message": log.message,
                        "data": log.data,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    })
                
                # حفظ مضغوط
                with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_file.name}")
                
                # إرسال للقناة
                await self.send_backup_to_channel(backup_file)
                
                return str(backup_file)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ خطأ في create_database_backup: {e}")
            return None
    
    async def send_backup_to_channel(self, backup_file: Path):
        """إرسال النسخة الاحتياطية لقناة تيليجرام"""
        try:
            # تشفير الملف أولاً
            encrypted_file = await self.encrypt_backup(backup_file)
            if not encrypted_file:
                return
            
            file_size = encrypted_file.stat().st_size
            
            if file_size > 50 * 1024 * 1024:  # أكبر من 50MB
                logger.warning(f"📦 الملف كبير جداً للإرسال: {file_size:,} بايت")
                return
            
            bot = Bot(token=Config.BOT_TOKEN)
            
            with open(encrypted_file, 'rb') as f:
                await bot.send_document(
                    chat_id=Config.LOG_CHANNEL,
                    document=f,
                    filename=f"backup_{datetime.now().strftime('%Y%m%d')}.enc",
                    caption=(
                        f"📦 <b>نسخة احتياطية</b>\n"
                        f"📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📊 <b>حجم الملف:</b> {file_size:,} بايت\n"
                        f"🔒 <b>مشفرة:</b> نعم\n\n"
                        f"<code>مفتاح فك التشفير: {Config.ENCRYPTION_KEY[:10]}...</code>"
                    ),
                    parse_mode='HTML'
                )
            
            logger.info("✅ تم إرسال النسخة الاحتياطية للقناة")
            
            # حذف الملفات المؤقتة
            encrypted_file.unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"❌ خطأ في send_backup_to_channel: {e}")
    
    async def encrypt_backup(self, backup_file: Path) -> Optional[Path]:
        """تشفير النسخة الاحتياطية"""
        try:
            encrypted_file = backup_file.with_suffix('.enc')
            
            # قراءة الملف
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                data = f.read()
            
            # تشفير
            encrypted_data = SecurityUtils.encrypt_data(data)
            
            # حفظ
            with open(encrypted_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            return encrypted_file
            
        except Exception as e:
            logger.error(f"❌ خطأ في encrypt_backup: {e}")
            return None
    
    async def generate_daily_report(self) -> Optional[str]:
        """توليد تقرير يومي"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            db = SessionLocal()
            try:
                # إحصائيات المستخدمين
                new_users = db.query(User).filter(
                    func.date(User.created_at) == yesterday
                ).count()
                
                active_users = db.query(User).filter(
                    User.updated_at >= datetime.combine(yesterday, datetime.min.time())
                ).count()
                
                # إحصائيات المعاملات
                deposits = db.query(Transaction).filter(
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed",
                    func.date(Transaction.created_at) == yesterday
                ).all()
                
                withdrawals = db.query(Transaction).filter(
                    Transaction.transaction_type == "withdraw",
                    Transaction.status == "completed",
                    func.date(Transaction.created_at) == yesterday
                ).all()
                
                total_deposits = sum(d.amount for d in deposits)
                total_withdrawals = sum(w.amount for w in withdrawals)
                
                # حسب طريقة الدفع
                payment_stats = {}
                for deposit in deposits:
                    method = deposit.payment_method or "unknown"
                    payment_stats[method] = payment_stats.get(method, 0) + deposit.amount
                
                # إنشاء التقرير
                report = {
                    "date": yesterday.isoformat(),
                    "users": {
                        "new": new_users,
                        "active": active_users,
                        "total": db.query(User).count()
                    },
                    "transactions": {
                        "deposits": {
                            "count": len(deposits),
                            "total_amount": total_deposits,
                            "average_amount": total_deposits / len(deposits) if deposits else 0
                        },
                        "withdrawals": {
                            "count": len(withdrawals),
                            "total_amount": total_withdrawals,
                            "average_amount": total_withdrawals / len(withdrawals) if withdrawals else 0
                        }
                    },
                    "payment_methods": payment_stats,
                    "summary": {
                        "net_flow": total_deposits - total_withdrawals,
                        "success_rate": (len(deposits) + len(withdrawals)) / 
                                       (db.query(Transaction).filter(
                                           func.date(Transaction.created_at) == yesterday
                                       ).count() or 1) * 100
                    }
                }
                
                # حفظ التقرير
                report_file = self.reports_dir / f"report_{yesterday.strftime('%Y%m%d')}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                
                # إرسال التقرير
                await self.send_report_to_channel(report, yesterday)
                
                logger.info(f"✅ تم إنشاء التقرير اليومي: {report_file.name}")
                return str(report_file)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ خطأ في generate_daily_report: {e}")
            return None
    
    async def send_report_to_channel(self, report: Dict, report_date):
        """إرسال التقرير للقناة"""
        try:
            message = f"""
📊 <b>التقرير اليومي</b>
📅 <b>التاريخ:</b> {report_date.strftime('%Y-%m-%d')}

👥 <b>المستخدمين:</b>
• 👤 جديد: <b>{report['users']['new']}</b>
• 🟢 نشط: <b>{report['users']['active']}</b>
• 📊 إجمالي: <b>{report['users']['total']}</b>

💳 <b>الإيداعات:</b>
• 🔢 عدد: <b>{report['transactions']['deposits']['count']}</b>
• 💰 إجمالي: <b>{report['transactions']['deposits']['total_amount']:,.0f}</b> ليرة
• 📈 متوسط: <b>{report['transactions']['deposits']['average_amount']:,.0f}</b> ليرة

💰 <b>السحوبات:</b>
• 🔢 عدد: <b>{report['transactions']['withdrawals']['count']}</b>
• 💸 إجمالي: <b>{report['transactions']['withdrawals']['total_amount']:,.0f}</b> ليرة
• 📉 متوسط: <b>{report['transactions']['withdrawals']['average_amount']:,.0f}</b> ليرة

📈 <b>التدفق الصافي:</b> <b>{report['summary']['net_flow']:,.0f}</b> ليرة
🎯 <b>معدل النجاح:</b> <b>{report['summary']['success_rate']:.1f}%</b>

💎 <b>طرق الدفع:</b>
"""
            
            for method, amount in report['payment_methods'].items():
                message += f"• {method}: <b>{amount:,.0f}</b> ليرة\n"
            
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=Config.REPORT_CHANNEL,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info("✅ تم إرسال التقرير اليومي للقناة")
            
        except Exception as e:
            logger.error(f"❌ خطأ في send_report_to_channel: {e}")
    
    async def generate_monthly_report(self, year: int = None, month: int = None):
        """توليد تقرير شهري"""
        try:
            now = datetime.now()
            if not year:
                year = now.year
            if not month:
                month = now.month
            
            db = SessionLocal()
            try:
                # حساب الفترة
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                
                # إحصائيات الشهر
                new_users = db.query(User).filter(
                    User.created_at >= start_date,
                    User.created_at < end_date
                ).count()
                
                total_deposits = db.query(func.sum(Transaction.amount)).filter(
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed",
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).scalar() or 0
                
                total_withdrawals = db.query(func.sum(Transaction.amount)).filter(
                    Transaction.transaction_type == "withdraw",
                    Transaction.status == "completed",
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).scalar() or 0
                
                # أعلى 10 مستخدمين
                top_users = db.query(
                    User.username,
                    User.first_name,
                    func.sum(Transaction.amount).label('total_deposits')
                ).join(
                    Transaction,
                    Transaction.user_id == User.id
                ).filter(
                    Transaction.transaction_type == "deposit",
                    Transaction.status == "completed",
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).group_by(
                    User.id
                ).order_by(
                    desc('total_deposits')
                ).limit(10).all()
                
                # إنشاء التقرير
                report = {
                    "period": {
                        "year": year,
                        "month": month,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "users": {
                        "new": new_users,
                        "total": db.query(User).filter(
                            User.created_at < end_date
                        ).count()
                    },
                    "transactions": {
                        "total_deposits": total_deposits,
                        "total_withdrawals": total_withdrawals,
                        "net_flow": total_deposits - total_withdrawals
                    },
                    "top_users": [
                        {
                            "username": u.username,
                            "first_name": u.first_name,
                            "total_deposits": u.total_deposits
                        }
                        for u in top_users
                    ]
                }
                
                # حفظ التقرير
                report_file = self.reports_dir / f"monthly_report_{year}_{month:02d}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ تم إنشاء التقرير الشهري: {report_file.name}")
                return str(report_file)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ خطأ في generate_monthly_report: {e}")
            return None
    
    async def cleanup_old_backups(self, days_to_keep: int = 30):
        """تنظيف النسخ الاحتياطية القديمة"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = 0
            for file in self.backup_dir.glob("*.json.gz"):
                if file.stat().st_mtime < cutoff_date.timestamp():
                    file.unlink()
                    deleted_count += 1
            
            for file in self.reports_dir.glob("*.json"):
                if file.stat().st_mtime < cutoff_date.timestamp():
                    file.unlink()
                    deleted_count += 1
            
            logger.info(f"🧹 تم حذف {deleted_count} ملف قديم")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في cleanup_old_backups: {e}")
            return 0

# مدير النسخ الاحتياطي العام
backup_manager = BackupManager()

async def schedule_backups():
    """جدولة النسخ الاحتياطية"""
    import schedule
    import time
    
    # نسخة احتياطية يومياً في 2 صباحاً
    schedule.every().day.at("02:00").do(
        lambda: asyncio.create_task(backup_manager.create_database_backup())
    )
    
    # تقرير يومي في منتصف الليل
    schedule.every().day.at("00:00").do(
        lambda: asyncio.create_task(backup_manager.generate_daily_report())
    )
    
    # تنظيف أسبوعي يوم الأحد 3 صباحاً
    schedule.every().sunday.at("03:00").do(
        lambda: asyncio.create_task(backup_manager.cleanup_old_backups())
    )
    
    logger.info("✅ تم جدولة النسخ الاحتياطية والتقارير")
    
    # تشغيل الجدولة
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

if __name__ == "__main__":
    # اختبار النسخ الاحتياطي
    import asyncio
    
    async def test():
        manager = BackupManager()
        
        print("🔧 اختبار النسخ الاحتياطي...")
        backup = await manager.create_database_backup()
        if backup:
            print(f"✅ تم إنشاء: {backup}")
        
        print("📊 اختبار التقرير اليومي...")
        report = await manager.generate_daily_report()
        if report:
            print(f"✅ تم إنشاء: {report}")
        
        print("🧹 تنظيف الملفات القديمة...")
        deleted = await manager.cleanup_old_backups(days_to_keep=1)
        print(f"✅ تم حذف {deleted} ملف")
    
    asyncio.run(test())