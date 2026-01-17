"""
معالجات المستخدمين المتقدمة
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_

from database.models import (
    SessionLocal, User, Transaction, Referral, 
    GiftCode, GiftTransaction, PaymentMethod
)
from config import Config
from utils.security import SecurityUtils
from utils.payments import payment_processor
from webhook.ichancy_webhook import ichancy_webhook

logger = logging.getLogger(__name__)

class UserHandlers:
    
    async def show_referral_menu(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User
    ):
        """عرض قائمة نظام الاحالات"""
        db = SessionLocal()
        try:
            # حساب الإحالات
            referrals = db.query(Referral).filter(
                Referral.referrer_id == user.id
            ).all()
            
            active_referrals = db.query(Referral).filter(
                Referral.referrer_id == user.id,
                Referral.is_active == True
            ).count()
            
            # حساب إجمالي الحرق من الإحالات النشطة
            total_burned = db.query(func.sum(Referral.total_burned)).filter(
                Referral.referrer_id == user.id,
                Referral.is_active == True
            ).scalar() or 0
            
            # حساب المكافآت المستقبلية
            potential_bonus = total_burned * (Config.REFERRAL_BONUS_PERCENT / 100)
            
            # بناء الرسالة
            message = f"""
👥 <b>نظام الاحالات</b>

📊 <b>إحصائياتك:</b>
• عدد الإحالات: <b>{len(referrals)}</b>
• الإحالات النشطة: <b>{active_referrals}</b>
• إجمالي الحرق: <b>{total_burned:,.0f}</b> ليرة
• المكافأة المتوقعة: <b>{potential_bonus:,.0f}</b> ليرة

🎯 <b>شروط الحصول على المكافآت:</b>
1. يجب أن يكون لديك <b>{Config.MIN_ACTIVE_REFERRALS} إحالات نشطة</b> على الأقل
2. كل إحالة يجب أن تحرق <b>{Config.MIN_BURN_AMOUNT:,.0f} ليرة</b> على الأقل
3. المكافأة توزع <b>شهرياً</b>

🔗 <b>رابط الإحالة الخاص بك:</b>
<code>https://t.me/{context.bot.username}?start={user.referral_code}</code>

📅 <b>موعد توزيع الجوائز القادم:</b>
آخر يوم من الشهر عند منتصف الليل

🎁 <b>مكافآت الإحالات:</b>
• لكل إحالة نشطة: <b>{Config.REFERRAL_BONUS_PERCENT}%</b> من حرقها
• لا حد أقصى للمكافآت!
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="refresh_referrals")],
                [InlineKeyboardButton("📋 قائمة الإحالات", callback_data="list_referrals")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
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
                
        except Exception as e:
            logger.error(f"خطأ في show_referral_menu: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض نظام الاحالات")
        finally:
            db.close()
    
    async def ask_gift_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """طلب إدخال كود الهدية"""
        context.user_data['awaiting_gift_code'] = True
        
        await update.message.reply_text(
            "🎁 <b>أدخل كود الهدية:</b>\n"
            "📝 <i>أدخل الكود الذي حصلت عليه</i>",
            parse_mode='HTML'
        )
    
    async def process_gift_code(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User,
        code: str
    ):
        """معالجة كود الهدية"""
        db = SessionLocal()
        try:
            success, message, amount = await payment_processor.process_gift_code(db, user.id, code)
            
            if success:
                # إرسال إشعار للإدمن
                await self._notify_admins(
                    f"🎁 <b>كود هدية مستخدم</b>\n"
                    f"👤 المستخدم: {user.username or user.first_name}\n"
                    f"💰 المبلغ: {amount:,.0f} ليرة\n"
                    f"🔢 الكود: {code.upper()}",
                    context
                )
            
            await update.message.reply_text(
                f"{'✅' if success else '❌'} <b>{message}</b>",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"خطأ في process_gift_code: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الكود")
        finally:
            db.close()
            context.user_data.pop('awaiting_gift_code', None)
    
    async def ask_gift_recipient(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """طلب إدخال معرف المستخدم المستقبل"""
        context.user_data['awaiting_gift_recipient'] = True
        
        await update.message.reply_text(
            "🎁 <b>إهداء رصيد</b>\n\n"
            "📝 <b>أدخل معرف المستخدم (User ID):</b>\n"
            "<i>يمكنك الحصول على ID المستخدم عن طريق:</i>\n"
            "1. إرسال /id للمستخدم\n"
            "2. أو استخدام معرفه الرقمي\n\n"
            "⚠️ <b>تحذير:</b> لا يمكن استرجاع الرصيد بعد الإرسال",
            parse_mode='HTML'
        )
    
    async def process_gift_recipient(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User,
        recipient_id: str
    ):
        """معالجة معرف المستقبل"""
        try:
            telegram_id = int(recipient_id)
            
            # منع الإهداء للنفس
            if telegram_id == user.telegram_id:
                await update.message.reply_text("❌ لا يمكن إهداء الرصيد لنفسك!")
                context.user_data.pop('awaiting_gift_recipient', None)
                context.user_data.pop('awaiting_gift_amount', None)
                return
            
            context.user_data['gift_recipient_id'] = telegram_id
            context.user_data.pop('awaiting_gift_recipient', None)
            context.user_data['awaiting_gift_amount'] = True
            
            await update.message.reply_text(
                f"✅ <b>تم تحديد المستخدم المستقبل</b>\n\n"
                f"💰 <b>أدخل المبلغ المراد إهداؤه:</b>\n"
                f"<i>الرصيد المتاح: {user.balance:,.0f} ليرة</i>",
                parse_mode='HTML'
            )
            
        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم غير صالح. يجب أن يكون رقماً.")
        except Exception as e:
            logger.error(f"خطأ في process_gift_recipient: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة معرف المستخدم")
    
    async def process_gift_amount(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User,
        amount: float
    ):
        """معالجة مبلغ الإهداء"""
        db = SessionLocal()
        try:
            recipient_id = context.user_data.get('gift_recipient_id')
            if not recipient_id:
                await update.message.reply_text("❌ لم يتم تحديد مستلم!")
                return
            
            # التحقق من الرصيد
            if user.balance < amount:
                await update.message.reply_text("❌ رصيدك غير كافي!")
                return
            
            # معالجة الإهداء
            success, message = await payment_processor.process_gift_balance(
                db, user.id, recipient_id, amount
            )
            
            if success:
                # إشعار للإدمن
                await self._notify_admins(
                    f"🎁 <b>إهداء رصيد</b>\n"
                    f"👤 المرسل: {user.username or user.first_name}\n"
                    f"👥 المستقبل: {recipient_id}\n"
                    f"💰 المبلغ: {amount:,.0f} ليرة\n"
                    f"📝 الرسالة: {message}",
                    context
                )
            
            await update.message.reply_text(
                f"{'✅' if success else '❌'} <b>{message}</b>",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"خطأ في process_gift_amount: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الإهداء")
        finally:
            db.close()
            # تنظيف البيانات المؤقتة
            context.user_data.pop('gift_recipient_id', None)
            context.user_data.pop('awaiting_gift_amount', None)
    
    async def show_contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض معلومات التواصل"""
        message = """
📞 <b>تواصل معنا</b>

🕐 <b>أوقات العمل:</b>
• يومياً: 10:00 صباحاً - 2:00 ليلاً

📧 <b>طرق التواصل:</b>
• الدعم الفني: @ichancy_support
• الإدارة: @ichancy_admin
• البريد الإلكتروني: support@ichancy.com

📍 <b>العنوان:</b>
دمشق، سوريا

⚠️ <b>ملاحظة:</b>
• للشكاوى المالية يرجى استخدام زر "تواصل مع الدعم"
• للاستفسارات العامة استخدم الروابط أعلاه
        """
        
        keyboard = [
            [InlineKeyboardButton("🆘 تواصل مع الدعم", callback_data="support_ticket")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def ask_support_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """طلب رسالة الدعم"""
        context.user_data['awaiting_support_message'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_support")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🆘 <b>تواصل مع الدعم الفني</b>\n\n"
            "📝 <b>أدخل رسالتك:</b>\n"
            "<i>يرجى وصف مشكلتك بالتفصيل، وسيتم الرد خلال 24 ساعة</i>\n\n"
            "⚠️ <b>للمشاكل المالية:</b>\n"
            "• أرفق رقم العملية\n"
            "• تاريخ العملية\n"
            "• المبلغ\n"
            "• طريقة الدفع",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def process_support_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: User,
        message: str
    ):
        """معالجة رسالة الدعم"""
        try:
            # إرسال رسالة الدعم لقناة الدعم
            support_message = f"""
🆘 <b>رسالة دعم جديدة</b>

👤 <b>المستخدم:</b> {user.username or user.first_name}
🆔 <b>ID:</b> <code>{user.telegram_id}</code>
📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 <b>الرسالة:</b>
{message[:500]}{'...' if len(message) > 500 else ''}

🎯 <b>الإجراءات:</b>
• الرد: /reply_{user.telegram_id}
• عرض المعلومات: /user_{user.telegram_id}
            """
            
            # إرسال للقناة (هنا نستخدم كود وهمي، سيتم استبداله)
            # await context.bot.send_message(chat_id=Config.SUPPORT_CHANNEL, ...)
            
            # تأكيد للمستخدم
            await update.message.reply_text(
                "✅ <b>تم إرسال رسالتك للدعم الفني</b>\n\n"
                "📨 <b>سيتم الرد عليك خلال 24 ساعة</b>\n"
                "🆔 <b>رقم التذكرة:</b> <code>SUP{}</code>".format(int(datetime.now().timestamp())),
                parse_mode='HTML'
            )
            
            # تسجيل في قاعدة البيانات
            db = SessionLocal()
            try:
                from database.models import SystemLog
                log = SystemLog(
                    log_level="INFO",
                    module="support",
                    message=f"رسالة دعم من {user.telegram_id}",
                    data={"message": message[:200]}
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"خطأ في process_support_message: {e}")
            await update.message.reply_text("❌ حدث خطأ في إرسال الرسالة")
        finally:
            context.user_data.pop('awaiting_support_message', None)
    
    async def show_transaction_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض سجل المعاملات"""
        db = SessionLocal()
        try:
            keyboard = [
                [
                    InlineKeyboardButton("💳 الإيداعات", callback_data="history_deposits"),
                    InlineKeyboardButton("💰 السحوبات", callback_data="history_withdrawals")
                ],
                [
                    InlineKeyboardButton("🎁 الهدايا", callback_data="history_gifts"),
                    InlineKeyboardButton("🎯 المكافآت", callback_data="history_bonuses")
                ],
                [InlineKeyboardButton("📊 الكل", callback_data="history_all")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # الحصول على أحدث المعاملات
            recent = db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).order_by(desc(Transaction.created_at)).limit(5).all()
            
            recent_text = ""
            for t in recent:
                icon = "💳" if t.transaction_type == "deposit" else "💰" if t.transaction_type == "withdraw" else "🎁"
                status = "✅" if t.status == "completed" else "⏳" if t.status == "pending" else "❌"
                recent_text += f"{icon} {status} {t.amount:,.0f} ليرة - {t.created_at.strftime('%d/%m %H:%M')}\n"
            
            message = f"""
📋 <b>سجل المعاملات</b>

💰 <b>رصيدك الحالي:</b> {user.balance:,.0f} ليرة
📊 <b>إجمالي الإيداعات:</b> {self._get_total_deposits(db, user.id):,.0f} ليرة
📊 <b>إجمالي السحوبات:</b> {self._get_total_withdrawals(db, user.id):,.0f} ليرة

🕐 <b>أحدث المعاملات:</b>
{recent_text if recent_text else "لا توجد معاملات سابقة"}

🔽 <b>اختر نوع السجل:</b>
            """
            
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_transaction_history: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض السجل")
        finally:
            db.close()
    
    async def show_tutorials(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض الشروحات"""
        tutorials = [
            {
                "title": "🎯 كيفية إنشاء حساب",
                "content": "1. اضغط على زر 'Ichancy'\n2. اختر 'إنشاء حساب'\n3. انتظر إنشاء الحساب\n4. احفظ بيانات الدخول"
            },
            {
                "title": "💳 كيفية شحن الرصيد",
                "content": "1. اختر 'شحن رصيد'\n2. اختر طريقة الدفع\n3. أدخل المبلغ\n4. اتبع التعليمات"
            },
            {
                "title": "💰 كيفية سحب الرصيد",
                "content": "1. اختر 'سحب رصيد'\n2. اختر طريقة السحب\n3. أدخل المبلغ\n4. أدخل رقم الحساب"
            },
            {
                "title": "👥 نظام الاحالات",
                "content": f"• احصل على {Config.REFERRAL_BONUS_PERCENT}% من حرق إحالاتك\n• تحتاج {Config.MIN_ACTIVE_REFERRALS} إحالات نشطة\n• كل إحالة تحتاج حرق {Config.MIN_BURN_AMOUNT:,.0f} ليرة"
            },
            {
                "title": "🎁 أكواد الهدايا",
                "content": "1. اختر 'كود هدية'\n2. أدخل الكود\n3. سيتم إضافة الرصيد تلقائياً"
            }
        ]
        
        keyboard = []
        for i, tutorial in enumerate(tutorials, 1):
            keyboard.append([InlineKeyboardButton(
                tutorial["title"], 
                callback_data=f"tutorial_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📚 <b>الشروحات والدروس</b>\n\n"
            "🔽 <b>اختر موضوعاً للتعلم:</b>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def show_betting_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض سجل الرهانات"""
        db = SessionLocal()
        try:
            if not user.ichancy_account_id:
                await update.message.reply_text(
                    "❌ <b>ليس لديك حساب Ichancy</b>\n\n"
                    "لعرض سجل الرهانات، تحتاج إلى:\n"
                    "1. إنشاء حساب Ichancy\n"
                    "2. القيام برهانات على المنصة\n"
                    "3. العودة هنا لعرض السجل",
                    parse_mode='HTML'
                )
                return
            
            # الحصول على سجل الرهانات من Ichancy
            result = await ichancy_webhook.get_account_balance(user.ichancy_account_id)
            
            if result["success"]:
                balance = result["balance"]
                
                # محاكاة سجل الرهانات (في الواقع سيتم جلبها من Ichancy)
                mock_bets = [
                    {"date": "2024-01-15", "amount": 1000, "type": "فوز", "game": "كورة"},
                    {"date": "2024-01-14", "amount": 500, "type": "خسارة", "game": "سلوتس"},
                    {"date": "2024-01-13", "amount": 2000, "type": "فوز", "game": "بوكر"},
                ]
                
                bets_text = ""
                total_won = 0
                total_lost = 0
                
                for bet in mock_bets:
                    icon = "🟢" if bet["type"] == "فوز" else "🔴"
                    bets_text += f"{icon} {bet['date']}: {bet['amount']:,.0f} ليرة ({bet['game']})\n"
                    
                    if bet["type"] == "فوز":
                        total_won += bet["amount"]
                    else:
                        total_lost += bet["amount"]
                
                message = f"""
⚡ <b>سجل الرهانات - Ichancy</b>

💰 <b>رصيد Ichancy الحالي:</b> {balance:,.0f} ليرة
🟢 <b>إجمالي الفوز:</b> {total_won:,.0f} ليرة
🔴 <b>إجمالي الخسارة:</b> {total_lost:,.0f} ليرة
📊 <b>صافي الربح:</b> {(total_won - total_lost):,.0f} ليرة

📋 <b>آخر الرهانات:</b>
{bets_text}

🆔 <b>رقم حسابك:</b> <code>{user.ichancy_account_id}</code>
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 تحديث السجل", callback_data="refresh_bets")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    "❌ <b>تعذر الاتصال بحساب Ichancy</b>\n"
                    "الرجاء المحاولة لاحقاً",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"خطأ في show_betting_history: {e}")
            await self.send_error_message(update, "حدث خطأ في عرض سجل الرهانات")
        finally:
            db.close()
    
    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض قائمة الإعدادات"""
        keyboard = [
            [
                InlineKeyboardButton("🔐 تغيير كلمة السر", callback_data="change_password"),
                InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications")
            ],
            [
                InlineKeyboardButton("🌐 اللغة", callback_data="language"),
                InlineKeyboardButton("🛡️ الخصوصية", callback_data="privacy")
            ],
            [InlineKeyboardButton("📋 بياناتي", callback_data="my_data")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
⚙️ <b>الإعدادات</b>

👤 <b>المستخدم:</b> {user.username or user.first_name}
🆔 <b>ID:</b> <code>{user.telegram_id}</code>
📅 <b>تاريخ التسجيل:</b> {user.created_at.strftime('%Y-%m-%d')}

🔒 <b>حالة الحساب:</b> {'✅ مفعل' if user.is_active else '❌ معطل'}
🚫 <b>الحظر:</b> {'❌ محظور' if user.is_banned else '✅ غير محظور'}

🔽 <b>اختر من القائمة:</b>
        """
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def handle_callback_query(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query_data: str,
        user: User
    ):
        """معالجة استعلامات Callback"""
        try:
            if query_data.startswith("history_"):
                await self.handle_history_callback(update, context, query_data, user)
            elif query_data.startswith("tutorial_"):
                await self.handle_tutorial_callback(update, context, query_data)
            elif query_data == "refresh_referrals":
                await self.show_referral_menu(update, context, user)
            elif query_data == "list_referrals":
                await self.show_referral_list(update, context, user)
            elif query_data == "refresh_bets":
                await self.show_betting_history(update, context, user)
            elif query_data == "cancel_support":
                context.user_data.pop('awaiting_support_message', None)
                await update.callback_query.message.edit_text("❌ تم إلغاء رسالة الدعم")
            elif query_data == "main_menu":
                await self.show_main_menu(update, context, user)
            else:
                await update.callback_query.answer("❌ الأمر غير معروف")
                
        except Exception as e:
            logger.error(f"خطأ في handle_callback_query: {e}")
            await update.callback_query.answer("❌ حدث خطأ")
    
    async def handle_history_callback(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query_data: str,
        user: User
    ):
        """معالجة callback السجل"""
        db = SessionLocal()
        try:
            type_filter = query_data.replace("history_", "")
            
            filters = {"user_id": user.id}
            if type_filter != "all":
                if type_filter == "deposits":
                    filters["transaction_type"] = "deposit"
                elif type_filter == "withdrawals":
                    filters["transaction_type"] = "withdraw"
                elif type_filter == "gifts":
                    filters["transaction_type"] = "gift"
                elif type_filter == "bonuses":
                    filters["transaction_type"] = "bonus"
            
            transactions = db.query(Transaction).filter_by(**filters).order_by(
                desc(Transaction.created_at)
            ).limit(20).all()
            
            if not transactions:
                await update.callback_query.message.edit_text(
                    "📭 <b>لا توجد معاملات</b>\n\n"
                    "لم تقم بأي معاملات من هذا النوع بعد.",
                    parse_mode='HTML'
                )
                return
            
            transactions_text = ""
            total = 0
            
            for t in transactions:
                icon = self._get_transaction_icon(t.transaction_type)
                status = self._get_status_icon(t.status)
                date = t.created_at.strftime('%d/%m %H:%M')
                
                transactions_text += f"{icon} {status} {t.amount:,.0f} ليرة - {date}\n"
                if t.status == "completed":
                    total += t.net_amount
            
            type_name = {
                "deposits": "الإيداعات",
                "withdrawals": "السحوبات", 
                "gifts": "الهدايا",
                "bonuses": "المكافآت",
                "all": "الكل"
            }.get(type_filter, "المعاملات")
            
            message = f"""
📋 <b>سجل {type_name}</b>

🔢 <b>عدد المعاملات:</b> {len(transactions)}
💰 <b>إجمالي المبالغ:</b> {total:,.0f} ليرة

📜 <b>المعاملات:</b>
{transactions_text}

⚠️ <i>عرض آخر 20 معاملة فقط</i>
            """
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع للسجل", callback_data="back_to_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في handle_history_callback: {e}")
            await update.callback_query.message.edit_text("❌ حدث خطأ في عرض السجل")
        finally:
            db.close()
    
    async def show_referral_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض قائمة الإحالات"""
        db = SessionLocal()
        try:
            referrals = db.query(Referral).filter(
                Referral.referrer_id == user.id
            ).options(joinedload(Referral.referred_user)).all()
            
            if not referrals:
                await update.callback_query.message.edit_text(
                    "📭 <b>لا توجد إحالات</b>\n\n"
                    "لم تقم بإحالة أي مستخدم بعد.\n"
                    "استخدم رابط الإحالة الخاص بك لجلب مستخدمين جدد.",
                    parse_mode='HTML'
                )
                return
            
            referrals_text = ""
            active_count = 0
            
            for ref in referrals:
                referred_user = ref.referred_user
                status = "🟢" if ref.is_active else "🔴"
                active_count += 1 if ref.is_active else 0
                
                referrals_text += f"{status} {referred_user.username or referred_user.first_name}"
                if ref.total_burned > 0:
                    referrals_text += f" - حرق: {ref.total_burned:,.0f} ليرة"
                referrals_text += "\n"
            
            message = f"""
👥 <b>قائمة الإحالات</b>

📊 <b>إجمالي الإحالات:</b> {len(referrals)}
🟢 <b>الإحالات النشطة:</b> {active_count}
🔴 <b>الإحالات غير النشطة:</b> {len(referrals) - active_count}

📋 <b>قائمة المستخدمين:</b>
{referrals_text}

🎯 <b>تفسير الألوان:</b>
🟢 = إحالة نشطة (تم الحرق)
🔴 = إحالة غير نشطة (لم يتم الحرق بعد)
            """
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_referrals")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في show_referral_list: {e}")
            await update.callback_query.message.edit_text("❌ حدث خطأ في عرض قائمة الإحالات")
        finally:
            db.close()
    
    async def handle_tutorial_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query_data: str):
        """معالجة callback الشروحات"""
        tutorials = [
            {
                "title": "🎯 كيفية إنشاء حساب",
                "content": """<b>🎯 كيفية إنشاء حساب Ichancy</b>

1️⃣ <b>اضغط على زر "Ichancy"</b> في القائمة الرئيسية
2️⃣ <b>اختر "إنشاء حساب Ichancy"</b>
3️⃣ <b>انتظر حتى ينشئ البوت الحساب</b> (قد يستغرق ثوانٍ)
4️⃣ <b>احفظ بيانات الدخول</b> التي سيرسلها البوت:
   • اسم المستخدم
   • كلمة السر
   • رقم الحساب

⚠️ <b>ملاحظات هامة:</b>
• بيانات الدخول تُرسل مرة واحدة فقط
• احفظها في مكان آمن
• لا تشاركها مع أحد
• يمكنك استخدام الحساب على موقع Ichancy

✅ <b>مميزات الحساب:</b>
• لعب جميع الألعاب
• المشاركة في المسابقات
• الحصول على مكافآت
• نظام الولاء"""
            },
            {
                "title": "💳 كيفية شحن الرصيد", 
                "content": """<b>💳 كيفية شحن الرصيد</b>

1️⃣ <b>اضغط على زر "شحن رصيد"</b> في القائمة الرئيسية
2️⃣ <b>اختر طريقة الدفع</b> المناسبة:
   • سيرياتيل كاش
   • شام كاش
   • شام كاش دولار
3️⃣ <b>أدخل المبلغ</b> المراد شحنه
4️⃣ <b>اتبع التعليمات</b> الخاصة بكل طريقة:

<b>لـ سيرياتيل كاش:</b>
• سيرسل لك البوت رقم سيرياتيل
• قم بالتحويل لهذا الرقم
• أرسل رقم العملية للبوت
• سيتم التأكيد تلقائياً

<b>لـ شام كاش:</b>
• قم بالتحويل للرقم المحدد
• أرسل رقم العملية للبوت
• انتظر موافقة الإدمن

💰 <b>معلومات مهمة:</b>
• الحد الأدنى: 500 ليرة
• الحد الأقصى: 50,000 ليرة
• العمولة: 0% (لا توجد عمولات)
• الوقت: من دقيقة إلى 15 دقيقة"""
            },
            # ... باقي الشروحات
        ]
        
        try:
            tutorial_num = int(query_data.replace("tutorial_", "")) - 1
            if 0 <= tutorial_num < len(tutorials):
                tutorial = tutorials[tutorial_num]
                
                keyboard = [[InlineKeyboardButton("🔙 رجوع للشروحات", callback_data="back_to_tutorials")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.message.edit_text(
                    tutorial["content"],
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await update.callback_query.answer("❌ الشرح غير موجود")
                
        except Exception as e:
            logger.error(f"خطأ في handle_tutorial_callback: {e}")
            await update.callback_query.answer("❌ حدث خطأ")
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض القائمة الرئيسية (منفصلة عن main_bot)"""
        from main_bot import IChancyBot
        bot = IChancyBot()
        await bot.show_main_menu(update, context, user)
    
    # ========== دوال مساعدة ==========
    
    def _get_total_deposits(self, db: Session, user_id: int) -> float:
        """الحصول على إجمالي الإيداعات"""
        total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "deposit",
            Transaction.status == "completed"
        ).scalar()
        return total or 0
    
    def _get_total_withdrawals(self, db: Session, user_id: int) -> float:
        """الحصول على إجمالي السحوبات"""
        total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "withdraw",
            Transaction.status == "completed"
        ).scalar()
        return total or 0
    
    def _get_transaction_icon(self, transaction_type: str) -> str:
        """الحصول على أيقونة المعاملة"""
        icons = {
            "deposit": "💳",
            "withdraw": "💰", 
            "gift": "🎁",
            "bonus": "🎯",
            "referral": "👥"
        }
        return icons.get(transaction_type, "📝")
    
    def _get_status_icon(self, status: str) -> str:
        """الحصول على أيقونة الحالة"""
        icons = {
            "completed": "✅",
            "pending": "⏳",
            "rejected": "❌",
            "canceled": "🚫"
        }
        return icons.get(status, "❓")
    
    async def _notify_admins(self, message: str, context: ContextTypes.DEFAULT_TYPE):
        """إرسال إشعار للإدمن"""
        try:
            for admin_id in Config.ADMIN_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار للإدمن: {e}")
    
    async def send_error_message(self, update: Update, message: str):
        """إرسال رسالة خطأ"""
        try:
            if update.callback_query:
                await update.callback_query.message.edit_text(f"❌ {message}")
            else:
                await update.message.reply_text(f"❌ {message}")
        except:
            pass

# نسخة عاملة للاستخدام
user_handlers = UserHandlers()