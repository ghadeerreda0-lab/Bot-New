"""
معالجات لوحة تحكم الإدمن
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, or_, and_
from sqlalchemy.exc import IntegrityError

from database.models import (
    SessionLocal, User, Transaction, Referral, 
    GiftCode, PaymentMethod, SyriatelCode, Bonus,
    AdminLog, SystemLog, GiftTransaction
)
from config import Config
from utils.security import SecurityUtils
from utils.payments import payment_processor
from webhook.ichancy_webhook import ichancy_webhook

logger = logging.getLogger(__name__)

class AdminHandlers:
    
    async def show_admin_panel(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        admin_user: User
    ):
        """عرض لوحة تحكم الإدمن"""
        if admin_user.telegram_id not in Config.ADMIN_IDS:
            await update.message.reply_text("❌ ليس لديك صلاحية الدخول هنا")
            return
        
        db = SessionLocal()
        try:
            # إحصائيات سريعة
            total_users = db.query(User).count()
            active_today = db.query(User).filter(
                User.updated_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            total_deposits = db.query(func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == "deposit",
                Transaction.status == "completed",
                Transaction.created_at >= datetime.utcnow() - timedelta(days=1)
            ).scalar() or 0
            
            total_withdrawals = db.query(func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == "withdraw",
                Transaction.status == "completed",
                Transaction.created_at >= datetime.utcnow() - timedelta(days=1)
            ).scalar() or 0
            
            pending_deposits = db.query(Transaction).filter(
                Transaction.transaction_type == "deposit",
                Transaction.status == "pending"
            ).count()
            
            pending_withdrawals = db.query(Transaction).filter(
                Transaction.transaction_type == "withdraw",
                Transaction.status == "pending"
            ).count()
            
            message = f"""
🛡️ <b>لوحة تحكم الإدمن</b>

👤 <b>مرحباً:</b> {admin_user.username or admin_user.first_name}
📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>إحصائيات اليوم:</b>
• 👥 إجمالي المستخدمين: <b>{total_users}</b>
• 🟢 المستخدمين النشطين: <b>{active_today}</b>
• 💳 إجمالي الإيداعات: <b>{total_deposits:,.0f}</b> ليرة
• 💰 إجمالي السحوبات: <b>{total_withdrawals:,.0f}</b> ليرة
• ⏳ طلبات إيداع بانتظار: <b>{pending_deposits}</b>
• ⏳ طلبات سحب بانتظار: <b>{pending_withdrawals}</b>

🔽 <b>اختر من القائمة:</b>
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
                    InlineKeyboardButton("💳 إدارة المعاملات", callback_data="admin_transactions")
                ],
                [
                    InlineKeyboardButton("⚙️ الإعدادات العامة", callback_data="admin_settings"),
                    InlineKeyboardButton("💰 إدارة الدفع", callback_data="admin_payments")
                ],
                [
                    InlineKeyboardButton("🎁 أكواد الهدايا", callback_data="admin_gift_codes"),
                    InlineKeyboardButton("👥 نظام الاحالات", callback_data="admin_referrals")
                ],
                [
                    InlineKeyboardButton("📊 التقارير والإحصائيات", callback_data="admin_reports"),
                    InlineKeyboardButton("📝 سجلات النظام", callback_data="admin_logs")
                ],
                [InlineKeyboardButton("🏠 الخروج للقائمة الرئيسية", callback_data="user_main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.message.edit_text(
                    message, 
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            
            # تسجيل دخول الإدمن
            await self.log_admin_action(
                admin_user.id, 
                "view_admin_panel", 
                {"section": "main"}
            )
                
        except Exception as e:
            logger.error(f"خطأ في show_admin_panel: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض لوحة التحكم")
        finally:
            db.close()
    
    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة المستخدمين"""
        db = SessionLocal()
        try:
            message = """
👥 <b>إدارة المستخدمين</b>

🔍 <b>عمليات البحث:</b>
• بحث باسم المستخدم
• بحث بـ ID
• بحث برقم الهاتف
• بحث بتاريخ التسجيل

⚡ <b>عمليات سريعة:</b>
• عرض جميع المستخدمين
• عرض المستخدمين النشطين
• عرض المستخدمين المحظورين
• عرض أعلى الأرصدة
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user"),
                    InlineKeyboardButton("📋 جميع المستخدمين", callback_data="admin_all_users")
                ],
                [
                    InlineKeyboardButton("🟢 المستخدمين النشطين", callback_data="admin_active_users"),
                    InlineKeyboardButton("🚫 المستخدمين المحظورين", callback_data="admin_banned_users")
                ],
                [
                    InlineKeyboardButton("💰 أعلى الأرصدة", callback_data="admin_top_balances"),
                    InlineKeyboardButton("🎯 أفضل اللاعبين", callback_data="admin_top_players")
                ],
                [
                    InlineKeyboardButton("➕ إضافة رصيد", callback_data="admin_add_balance"),
                    InlineKeyboardButton("➖ سحب رصيد", callback_data="admin_remove_balance")
                ],
                [
                    InlineKeyboardButton("📨 إرسال رسالة", callback_data="admin_send_message"),
                    InlineKeyboardButton("📸 إرسال صورة", callback_data="admin_send_photo")
                ],
                [
                    InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user"),
                    InlineKeyboardButton("✅ فك حظر", callback_data="admin_unban_user")
                ],
                [
                    InlineKeyboardButton("🗑️ حذف حساب", callback_data="admin_delete_user"),
                    InlineKeyboardButton("🔄 تحديث بيانات", callback_data="admin_refresh_users")
                ],
                [InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_user_management: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض إدارة المستخدمين")
        finally:
            db.close()
    
    async def search_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """البحث عن مستخدم"""
        context.user_data['admin_action'] = 'search_user'
        context.user_data['awaiting_input'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_users")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            "🔍 <b>البحث عن مستخدم</b>\n\n"
            "📝 <b>أدخل إحدى المعلومات التالية:</b>\n"
            "• معرف التلجرام (User ID)\n"
            "• اسم المستخدم (Username)\n"
            "• الاسم الأول\n"
            "• رقم الحساب\n"
            "• كود الإحالة\n\n"
            "💡 <i>يمكنك البحث بأي جزء من المعلومات</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def process_user_search(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        search_term: str
    ):
        """معالجة بحث المستخدم"""
        db = SessionLocal()
        try:
            # البحث بعدة طرق
            users = db.query(User).filter(
                or_(
                    User.telegram_id.cast(db.String).like(f"%{search_term}%"),
                    User.username.ilike(f"%{search_term}%"),
                    User.first_name.ilike(f"%{search_term}%"),
                    User.last_name.ilike(f"%{search_term}%"),
                    User.ichancy_account_id.ilike(f"%{search_term}%"),
                    User.referral_code.ilike(f"%{search_term}%")
                )
            ).limit(20).all()
            
            if not users:
                await update.message.reply_text(
                    "❌ <b>لم يتم العثور على مستخدمين</b>\n\n"
                    "جرب بحثاً مختلفاً أو استخدم المعرف الكامل.",
                    parse_mode='HTML'
                )
                return
            
            if len(users) == 1:
                # عرض تفاصيل المستخدم الواحد
                await self.show_user_details(update, context, users[0])
            else:
                # عرض قائمة المستخدمين
                users_list = ""
                for i, user in enumerate(users, 1):
                    status = "🟢" if user.is_active else "🔴"
                    banned = "🚫" if user.is_banned else ""
                    users_list += f"{i}. {status} {banned} {user.username or user.first_name} (ID: {user.telegram_id})\n"
                
                message = f"""
🔍 <b>نتائج البحث:</b> "{search_term}"

👥 <b>عدد النتائج:</b> {len(users)}
📋 <b>القائمة:</b>
{users_list}

📝 <b>لتحديد مستخدم:</b>
أرسل رقمه من القائمة (مثال: 1)
                """
                
                context.user_data['search_results'] = {
                    str(i): user.id for i, user in enumerate(users, 1)
                }
                context.user_data['awaiting_user_selection'] = True
                
                await update.message.reply_text(
                    message,
                    parse_mode='HTML'
                )
            
        except Exception as e:
            logger.error(f"خطأ في process_user_search: {e}")
            await update.message.reply_text("❌ حدث خطأ في البحث")
        finally:
            db.close()
            context.user_data.pop('admin_action', None)
            context.user_data.pop('awaiting_input', None)
    
    async def show_user_details(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User
    ):
        """عرض تفاصيل مستخدم"""
        db = SessionLocal()
        try:
            # إحصائيات المستخدم
            total_deposits = db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == "deposit",
                Transaction.status == "completed"
            ).scalar() or 0
            
            total_withdrawals = db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user.id,
                Transaction.transaction_type == "withdraw",
                Transaction.status == "completed"
            ).scalar() or 0
            
            referrals_count = db.query(Referral).filter(
                Referral.referrer_id == user.id
            ).count()
            
            active_referrals = db.query(Referral).filter(
                Referral.referrer_id == user.id,
                Referral.is_active == True
            ).count()
            
            # آخر معاملة
            last_transaction = db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).order_by(desc(Transaction.created_at)).first()
            
            last_transaction_text = ""
            if last_transaction:
                icon = "💳" if last_transaction.transaction_type == "deposit" else "💰"
                last_transaction_text = f"{icon} {last_transaction.amount:,.0f} ليرة - {last_transaction.created_at.strftime('%d/%m %H:%M')}"
            
            message = f"""
👤 <b>تفاصيل المستخدم</b>

🆔 <b>معرف التلجرام:</b> <code>{user.telegram_id}</code>
👤 <b>اسم المستخدم:</b> @{user.username or 'لا يوجد'}
👤 <b>الاسم:</b> {user.first_name} {user.last_name or ''}

💰 <b>المعلومات المالية:</b>
• الرصيد الحالي: <b>{user.balance:,.0f}</b> ليرة
• إجمالي الإيداعات: <b>{total_deposits:,.0f}</b> ليرة
• إجمالي السحوبات: <b>{total_withdrawals:,.0f}</b> ليرة
• آخر معاملة: {last_transaction_text}

📊 <b>إحصائيات أخرى:</b>
• تاريخ التسجيل: {user.created_at.strftime('%Y-%m-%d %H:%M')}
• آخر نشاط: {user.updated_at.strftime('%Y-%m-%d %H:%M')}
• عدد الإحالات: {referrals_count} ({active_referrals} نشطة)

🎯 <b>حساب Ichancy:</b>
{'✅ مرتبط' if user.ichancy_account_id else '❌ غير مرتبط'}
{'🆔 رقم الحساب: ' + user.ichancy_account_id if user.ichancy_account_id else ''}
{'👤 اسم المستخدم: ' + user.ichancy_username if user.ichancy_username else ''}

🚫 <b>حالة الحساب:</b>
• {'✅ مفعل' if user.is_active else '❌ معطل'}
• {'🚫 محظور' if user.is_banned else '✅ غير محظور'}

🔗 <b>كود الإحالة:</b> <code>{user.referral_code}</code>
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ إضافة رصيد", callback_data=f"admin_addbal_{user.id}"),
                    InlineKeyboardButton("➖ سحب رصيد", callback_data=f"admin_removebal_{user.id}")
                ],
                [
                    InlineKeyboardButton("📨 إرسال رسالة", callback_data=f"admin_sendmsg_{user.id}"),
                    InlineKeyboardButton("📸 إرسال صورة", callback_data=f"admin_sendphoto_{user.id}")
                ],
                [
                    InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_{user.id}") if not user.is_banned 
                    else InlineKeyboardButton("✅ فك حظر", callback_data=f"admin_unban_{user.id}"),
                    InlineKeyboardButton("🗑️ حذف حساب", callback_data=f"admin_delete_{user.id}")
                ],
                [
                    InlineKeyboardButton("📋 سجل المعاملات", callback_data=f"admin_transactions_{user.id}"),
                    InlineKeyboardButton("👥 الإحالات", callback_data=f"admin_referrals_{user.id}")
                ],
                [InlineKeyboardButton("🔙 رجوع لإدارة المستخدمين", callback_data="admin_users")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.message.edit_text(
                    message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            
            # حفظ معرف المستخدم الحالي
            context.user_data['current_user_id'] = user.id
            
        except Exception as e:
            logger.error(f"خطأ في show_user_details: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض تفاصيل المستخدم")
        finally:
            db.close()
    
    async def add_user_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """إضافة رصيد لمستخدم"""
        context.user_data['admin_action'] = 'add_balance'
        context.user_data['target_user_id'] = user_id
        context.user_data['awaiting_input'] = True
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await update.callback_query.answer("❌ المستخدم غير موجود")
                return
            
            keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data=f"admin_user_details_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                f"➕ <b>إضافة رصيد للمستخدم</b>\n\n"
                f"👤 <b>المستخدم:</b> {user.username or user.first_name}\n"
                f"💰 <b>الرصيد الحالي:</b> {user.balance:,.0f} ليرة\n\n"
                f"💵 <b>أدخل المبلغ المراد إضافته:</b>\n"
                f"<i>يمكنك إضافة كسور (مثال: 1000.5)</i>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في add_user_balance: {e}")
            await update.callback_query.answer("❌ حدث خطأ")
        finally:
            db.close()
    
    async def process_add_balance(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        admin_user: User,
        amount: float
    ):
        """معالجة إضافة الرصيد"""
        db = SessionLocal()
        try:
            user_id = context.user_data.get('target_user_id')
            if not user_id:
                await update.message.reply_text("❌ لم يتم تحديد مستخدم!")
                return
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                return
            
            if amount <= 0:
                await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من الصفر!")
                return
            
            # إضافة الرصيد
            old_balance = user.balance
            user.balance += amount
            user.updated_at = datetime.utcnow()
            
            # تسجيل المعاملة
            transaction = Transaction(
                user_id=user.id,
                transaction_type="deposit",
                amount=amount,
                fee=0,
                net_amount=amount,
                payment_method="admin_add",
                status="completed",
                admin_id=admin_user.id,
                auto_verified=False,
                notes=f"إضافة يدوية من الإدمن {admin_user.username}",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            db.add(transaction)
            db.commit()
            
            # إشعار المستخدم
            await self.notify_user_balance_added(context, user, amount, old_balance)
            
            # تسجيل عمل الإدمن
            await self.log_admin_action(
                admin_user.id,
                "add_balance",
                {
                    "target_user_id": user.id,
                    "target_telegram_id": user.telegram_id,
                    "amount": amount,
                    "old_balance": old_balance,
                    "new_balance": user.balance
                }
            )
            
            # رسالة تأكيد للإدمن
            await update.message.reply_text(
                f"✅ <b>تم إضافة الرصيد بنجاح</b>\n\n"
                f"👤 <b>المستخدم:</b> {user.username or user.first_name}\n"
                f"💰 <b>المبلغ المضاف:</b> {amount:,.0f} ليرة\n"
                f"📊 <b>الرصيد السابق:</b> {old_balance:,.0f} ليرة\n"
                f"📈 <b>الرصيد الجديد:</b> {user.balance:,.0f} ليرة\n\n"
                f"🆔 <b>رقم المعاملة:</b> <code>{transaction.id}</code>",
                parse_mode='HTML'
            )
            
            # تنظيف البيانات
            context.user_data.pop('admin_action', None)
            context.user_data.pop('target_user_id', None)
            context.user_data.pop('awaiting_input', None)
            
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في process_add_balance: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الرصيد")
        finally:
            db.close()
    
    async def show_transaction_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة المعاملات"""
        db = SessionLocal()
        try:
            # إحصائيات سريعة
            pending_deposits = db.query(Transaction).filter(
                Transaction.transaction_type == "deposit",
                Transaction.status == "pending"
            ).count()
            
            pending_withdrawals = db.query(Transaction).filter(
                Transaction.transaction_type == "withdraw",
                Transaction.status == "pending"
            ).count()
            
            today_deposits = db.query(func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == "deposit",
                Transaction.status == "completed",
                Transaction.created_at >= datetime.utcnow().date()
            ).scalar() or 0
            
            today_withdrawals = db.query(func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == "withdraw",
                Transaction.status == "completed",
                Transaction.created_at >= datetime.utcnow().date()
            ).scalar() or 0
            
            message = f"""
💳 <b>إدارة المعاملات</b>

📊 <b>إحصائيات اليوم:</b>
• 💰 الإيداعات المعلقة: <b>{pending_deposits}</b>
• 💸 السحوبات المعلقة: <b>{pending_withdrawals}</b>
• 📈 إجمالي الإيداعات: <b>{today_deposits:,.0f}</b> ليرة
• 📉 إجمالي السحوبات: <b>{today_withdrawals:,.0f}</b> ليرة

🔽 <b>اختر من القائمة:</b>
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("⏳ طلبات الإيداع المعلقة", callback_data="admin_pending_deposits"),
                    InlineKeyboardButton("⏳ طلبات السحب المعلقة", callback_data="admin_pending_withdrawals")
                ],
                [
                    InlineKeyboardButton("📋 جميع المعاملات", callback_data="admin_all_transactions"),
                    InlineKeyboardButton("🔍 بحث في المعاملات", callback_data="admin_search_transactions")
                ],
                [
                    InlineKeyboardButton("✅ تأكيد معاملة", callback_data="admin_confirm_transaction"),
                    InlineKeyboardButton("❌ رفض معاملة", callback_data="admin_reject_transaction")
                ],
                [
                    InlineKeyboardButton("💰 عمليات اليوم", callback_data="admin_today_transactions"),
                    InlineKeyboardButton("📅 عمليات الشهر", callback_data="admin_month_transactions")
                ],
                [
                    InlineKeyboardButton("🧾 تصدير تقرير", callback_data="admin_export_transactions"),
                    InlineKeyboardButton("🔄 تحديث", callback_data="admin_refresh_transactions")
                ],
                [InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_transaction_management: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض إدارة المعاملات")
        finally:
            db.close()
    
    async def show_pending_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض طلبات الإيداع المعلقة"""
        db = SessionLocal()
        try:
            deposits = db.query(Transaction).filter(
                Transaction.transaction_type == "deposit",
                Transaction.status == "pending"
            ).options(joinedload(Transaction.user)).order_by(
                asc(Transaction.created_at)
            ).limit(50).all()
            
            if not deposits:
                await update.callback_query.message.edit_text(
                    "✅ <b>لا توجد طلبات إيداع معلقة</b>\n\n"
                    "جميع طلبات الإيداع تمت معالجتها.",
                    parse_mode='HTML'
                )
                return
            
            deposits_list = ""
            for i, deposit in enumerate(deposits, 1):
                user = deposit.user
                time_ago = self._get_time_ago(deposit.created_at)
                
                deposits_list += (
                    f"{i}. 💰 <b>{deposit.amount:,.0f}</b> ليرة\n"
                    f"   👤 {user.username or user.first_name} (ID: {user.telegram_id})\n"
                    f"   ⏰ {time_ago}\n"
                    f"   🆔 <code>{deposit.id}</code>\n\n"
                )
            
            message = f"""
⏳ <b>طلبات الإيداع المعلقة</b>

📊 <b>عدد الطلبات:</b> {len(deposits)}

📋 <b>قائمة الطلبات:</b>
{deposits_list}

📝 <b>للتأكيد أو الرفض:</b>
أرسل رقم الطلب متبوعاً بـ ✅ أو ❌
مثال: "1 ✅" أو "2 ❌"

💡 <b>معلومات:</b>
• يتم عرض آخر 50 طلب فقط
• الطلبات مرتبة من الأقدم للأحدث
            """
            
            context.user_data['pending_deposits'] = {
                str(i): deposit.id for i, deposit in enumerate(deposits, 1)
            }
            context.user_data['awaiting_deposit_action'] = True
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_transactions")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_pending_deposits: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض طلبات الإيداع")
        finally:
            db.close()
    
    async def process_deposit_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        admin_user: User,
        action_data: str
    ):
        """معالجة إجراء على طلب إيداع"""
        try:
            parts = action_data.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ صيغة غير صحيحة. مثال: '1 ✅'")
                return
            
            deposit_num = parts[0]
            action = parts[1]
            
            if action not in ["✅", "❌"]:
                await update.message.reply_text("❌ إجراء غير صالح. استخدم ✅ أو ❌")
                return
            
            deposits_map = context.user_data.get('pending_deposits', {})
            if deposit_num not in deposits_map:
                await update.message.reply_text("❌ رقم الطلب غير صحيح")
                return
            
            deposit_id = deposits_map[deposit_num]
            
            db = SessionLocal()
            try:
                deposit = db.query(Transaction).filter(Transaction.id == deposit_id).first()
                if not deposit or deposit.status != "pending":
                    await update.message.reply_text("❌ الطلب غير موجود أو تمت معالجته مسبقاً")
                    return
                
                user = deposit.user
                
                if action == "✅":
                    # تأكيد الطلب
                    deposit.status = "completed"
                    deposit.admin_id = admin_user.id
                    deposit.completed_at = datetime.utcnow()
                    
                    # تحديث رصيد المستخدم
                    user.balance += deposit.net_amount
                    user.updated_at = datetime.utcnow()
                    
                    db.commit()
                    
                    # إشعار المستخدم
                    await self.notify_user_deposit_confirmed(context, user, deposit)
                    
                    # تسجيل عمل الإدمن
                    await self.log_admin_action(
                        admin_user.id,
                        "confirm_deposit",
                        {
                            "transaction_id": deposit.id,
                            "user_id": user.id,
                            "amount": deposit.amount,
                            "net_amount": deposit.net_amount
                        }
                    )
                    
                    await update.message.reply_text(
                        f"✅ <b>تم تأكيد طلب الإيداع بنجاح</b>\n\n"
                        f"💰 <b>المبلغ:</b> {deposit.amount:,.0f} ليرة\n"
                        f"👤 <b>المستخدم:</b> {user.username or user.first_name}\n"
                        f"📊 <b>الرصيد الجديد:</b> {user.balance:,.0f} ليرة\n"
                        f"🆔 <b>رقم المعاملة:</b> <code>{deposit.id}</code>",
                        parse_mode='HTML'
                    )
                    
                else:  # ❌
                    # رفض الطلب
                    deposit.status = "rejected"
                    deposit.admin_id = admin_user.id
                    deposit.completed_at = datetime.utcnow()
                    
                    db.commit()
                    
                    # إشعار المستخدم
                    await self.notify_user_deposit_rejected(context, user, deposit)
                    
                    # تسجيل عمل الإدمن
                    await self.log_admin_action(
                        admin_user.id,
                        "reject_deposit",
                        {
                            "transaction_id": deposit.id,
                            "user_id": user.id,
                            "amount": deposit.amount
                        }
                    )
                    
                    await update.message.reply_text(
                        f"❌ <b>تم رفض طلب الإيداع</b>\n\n"
                        f"💰 <b>المبلغ:</b> {deposit.amount:,.0f} ليرة\n"
                        f"👤 <b>المستخدم:</b> {user.username or user.first_name}\n"
                        f"🆔 <b>رقم المعاملة:</b> <code>{deposit.id}</code>",
                        parse_mode='HTML'
                    )
                
                # تنظيف البيانات
                context.user_data.pop('pending_deposits', None)
                context.user_data.pop('awaiting_deposit_action', None)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"خطأ في process_deposit_action: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الطلب")
    
    async def show_settings_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الإعدادات العامة"""
        message = """
⚙️ <b>الإعدادات العامة</b>

🔧 <b>إعدادات النظام:</b>
• إعدادات Ichancy
• إعدادات الدفع
• إعدادات السحب
• إعدادات المستخدمين
• إعدادات الاحالات

🔐 <b>الأمان:</b>
• إدارة الإدمن
• سجلات النظام
• إعدادات الحماية
• النسخ الاحتياطي

📊 <b>التقارير:</b>
• إعدادات التقارير
• توقيت التقارير
• قنوات الإشعارات
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🤖 Ichancy", callback_data="admin_ichancy_settings"),
                InlineKeyboardButton("💳 الدفع", callback_data="admin_payment_settings")
            ],
            [
                InlineKeyboardButton("💰 السحب", callback_data="admin_withdrawal_settings"),
                InlineKeyboardButton("👥 المستخدمين", callback_data="admin_user_settings")
            ],
            [
                InlineKeyboardButton("👥 الاحالات", callback_data="admin_referral_settings"),
                InlineKeyboardButton("🛡️ الأمان", callback_data="admin_security_settings")
            ],
            [
                InlineKeyboardButton("📊 التقارير", callback_data="admin_report_settings"),
                InlineKeyboardButton("🔔 الإشعارات", callback_data="admin_notification_settings")
            ],
            [
                InlineKeyboardButton("🔄 إعادة تعيين", callback_data="admin_reset_settings"),
                InlineKeyboardButton("💾 نسخ احتياطي", callback_data="admin_backup")
            ],
            [InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_payment_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة الدفع"""
        db = SessionLocal()
        try:
            payment_methods = db.query(PaymentMethod).order_by(PaymentMethod.id).all()
            
            methods_text = ""
            for method in payment_methods:
                status = "✅" if method.is_active else "❌"
                methods_text += f"{status} <b>{method.display_name}</b> ({method.name})\n"
            
            syriatel_codes = db.query(SyriatelCode).filter(
                SyriatelCode.is_active == True
            ).count()
            
            total_syriatel_balance = db.query(func.sum(SyriatelCode.current_balance)).filter(
                SyriatelCode.is_active == True
            ).scalar() or 0
            
            total_syriatel_capacity = db.query(func.sum(SyriatelCode.max_balance)).filter(
                SyriatelCode.is_active == True
            ).scalar() or 0
            
            message = f"""
💰 <b>إدارة الدفع</b>

💳 <b>طرق الدفع المتاحة:</b>
{methods_text}

📱 <b>سيرياتيل كاش:</b>
• عدد الأكواد النشطة: <b>{syriatel_codes}</b>
• إجمالي الرصيد المستخدم: <b>{total_syriatel_balance:,.0f}</b> ليرة
• السعة الإجمالية: <b>{total_syriatel_capacity:,.0f}</b> ليرة
• السعة المتبقية: <b>{(total_syriatel_capacity - total_syriatel_balance):,.0f}</b> ليرة

🔽 <b>اختر من القائمة:</b>
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ إضافة طريقة دفع", callback_data="admin_add_payment_method"),
                    InlineKeyboardButton("⚙️ تعديل طرق الدفع", callback_data="admin_edit_payment_methods")
                ],
                [
                    InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="admin_syriatel_settings"),
                    InlineKeyboardButton("💎 شام كاش", callback_data="admin_cham_settings")
                ],
                [
                    InlineKeyboardButton("💲 شام دولار", callback_data="admin_cham_usd_settings"),
                    InlineKeyboardButton("🎁 البونصات", callback_data="admin_bonus_settings")
                ],
                [
                    InlineKeyboardButton("🧾 إدارة الأكواد", callback_data="admin_codes_management"),
                    InlineKeyboardButton("🔄 تصفير الأكواد", callback_data="admin_reset_codes")
                ],
                [
                    InlineKeyboardButton("📊 إحصائيات الدفع", callback_data="admin_payment_stats"),
                    InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_payment_management: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض إدارة الدفع")
        finally:
            db.close()
    
    async def handle_admin_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query_data: str,
        admin_user: User
    ):
        """معالجة استعلامات الإدمن"""
        try:
            if query_data == "admin_panel":
                await self.show_admin_panel(update, context, admin_user)
            elif query_data == "admin_users":
                await self.show_user_management(update, context)
            elif query_data == "admin_transactions":
                await self.show_transaction_management(update, context)
            elif query_data == "admin_settings":
                await self.show_settings_management(update, context)
            elif query_data == "admin_payments":
                await self.show_payment_management(update, context)
            elif query_data == "admin_gift_codes":
                await self.show_gift_codes_management(update, context)
            elif query_data == "admin_referrals":
                await self.show_referral_management(update, context)
            elif query_data == "admin_reports":
                await self.show_reports_management(update, context)
            elif query_data == "admin_logs":
                await self.show_logs_management(update, context)
            elif query_data == "admin_search_user":
                await self.search_user(update, context)
            elif query_data == "admin_pending_deposits":
                await self.show_pending_deposits(update, context)
            elif query_data.startswith("admin_addbal_"):
                user_id = int(query_data.replace("admin_addbal_", ""))
                await self.add_user_balance(update, context, user_id)
            elif query_data == "user_main_menu":
                from main_bot import IChancyBot
                bot = IChancyBot()
                await bot.show_main_menu(update, context, admin_user)
            else:
                await update.callback_query.answer("❌ الأمر غير معروف")
                
        except Exception as e:
            logger.error(f"خطأ في handle_admin_callback: {e}")
            await update.callback_query.answer("❌ حدث خطأ")
    
    async def process_admin_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        admin_user: User,
        text: str
    ):
        """معالجة إدخال الإدمن"""
        try:
            action = context.user_data.get('admin_action')
            
            if action == 'search_user':
                await self.process_user_search(update, context, text)
            elif action == 'add_balance':
                try:
                    amount = float(text)
                    await self.process_add_balance(update, context, admin_user, amount)
                except ValueError:
                    await update.message.reply_text("❌ المبلغ يجب أن يكون رقماً!")
            elif action == 'awaiting_deposit_action':
                await self.process_deposit_action(update, context, admin_user, text)
            elif 'awaiting_user_selection' in context.user_data:
                await self.process_user_selection(update, context, text)
            else:
                await update.message.reply_text("❌ لا يوجد إجراء بانتظار الإدخال")
                
        except Exception as e:
            logger.error(f"خطأ في process_admin_input: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الإدخال")
    
    async def process_user_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selection: str):
        """معالجة اختيار مستخدم من القائمة"""
        try:
            users_map = context.user_data.get('search_results', {})
            if selection not in users_map:
                await update.message.reply_text("❌ الرقم غير صحيح!")
                return
            
            user_id = users_map[selection]
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    await self.show_user_details(update, context, user)
            finally:
                db.close()
            
            # تنظيف البيانات
            context.user_data.pop('search_results', None)
            context.user_data.pop('awaiting_user_selection', None)
            
        except Exception as e:
            logger.error(f"خطأ في process_user_selection: {e}")
            await update.message.reply_text("❌ حدث خطأ في اختيار المستخدم")
    
    # ========== دوال مساعدة ==========
    
    def _get_time_ago(self, dt: datetime) -> str:
        """الحصول على الوقت المنقضي"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"قبل {diff.days} يوم"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"قبل {hours} ساعة"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"قبل {minutes} دقيقة"
        else:
            return "الآن"
    
    async def notify_user_balance_added(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user: User,
        amount: float,
        old_balance: float
    ):
        """إشعار المستخدم بإضافة رصيد"""
        try:
            message = (
                f"✅ <b>تم إضافة رصيد لحسابك</b>\n\n"
                f"💰 <b>المبلغ المضاف:</b> {amount:,.0f} ليرة\n"
                f"📊 <b>الرصيد السابق:</b> {old_balance:,.0f} ليرة\n"
                f"📈 <b>الرصيد الجديد:</b> {user.balance:,.0f} ليرة\n\n"
                f"🕐 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"👤 <b>بواسطة:</b> الإدارة"
            )
            
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"خطأ في notify_user_balance_added: {e}")
    
    async def notify_user_deposit_confirmed(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user: User,
        deposit: Transaction
    ):
        """إشعار المستخدم بتأكيد الإيداع"""
        try:
            message = (
                f"✅ <b>تم تأكيد طلب الإيداع</b>\n\n"
                f"💰 <b>المبلغ:</b> {deposit.amount:,.0f} ليرة\n"
                f"📊 <b>الرصيد الجديد:</b> {user.balance:,.0f} ليرة\n"
                f"🆔 <b>رقم العملية:</b> <code>{deposit.transaction_code}</code>\n\n"
                f"🕐 <b>التاريخ:</b> {deposit.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"خطأ في notify_user_deposit_confirmed: {e}")
    
    async def notify_user_deposit_rejected(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user: User,
        deposit: Transaction
    ):
        """إشعار المستخدم برفض الإيداع"""
        try:
            message = (
                f"❌ <b>تم رفض طلب الإيداع</b>\n\n"
                f"💰 <b>المبلغ:</b> {deposit.amount:,.0f} ليرة\n"
                f"🆔 <b>رقم العملية:</b> <code>{deposit.transaction_code}</code>\n\n"
                f"🕐 <b>التاريخ:</b> {deposit.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📞 <b>للاستفسار:</b> تواصل مع الدعم"
            )
            
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"خطأ في notify_user_deposit_rejected: {e}")
    
    async def log_admin_action(
        self,
        admin_id: int,
        action_type: str,
        details: Dict
    ):
        """تسجيل إجراء الإدمن"""
        db = SessionLocal()
        try:
            log = AdminLog(
                admin_id=admin_id,
                action_type=action_type,
                details=details,
                created_at=datetime.utcnow()
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"خطأ في log_admin_action: {e}")
        finally:
            db.close()
    
    async def send_error_message(self, update: Update, message: str):
        """إرسال رسالة خطأ"""
        try:
            if update.callback_query:
                await update.callback_query.message.edit_text(f"❌ {message}")
            else:
                await update.message.reply_text(f"❌ {message}")
        except:
            pass
    
    async def show_gift_codes_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة أكواد الهدايا"""
        # سيتم تنفيذها لاحقاً
        await update.callback_query.message.edit_text("⏳ قيد التطوير...")
    
    async def show_referral_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة نظام الاحالات"""
        # سيتم تنفيذها لاحقاً
        await update.callback_query.message.edit_text("⏳ قيد التطوير...")
    
    async def show_reports_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة التقارير"""
        # سيتم تنفيذها لاحقاً
        await update.callback_query.message.edit_text("⏳ قيد التطوير...")
    
    async def show_logs_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إدارة سجلات النظام"""
        # سيتم تنفيذها لاحقاً
        await update.callback_query.message.edit_text("⏳ قيد التطوير...")

# نسخة عاملة للاستخدام
admin_handlers = AdminHandlers()