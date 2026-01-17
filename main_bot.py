"""
البوت الرئيسي - Telegram Bot
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from config import Config, logger
from database.models import SessionLocal, User, Transaction, PaymentMethod
from utils.security import generate_referral_code, encrypt_data, decrypt_data
from utils.payments import PaymentProcessor
from handlers.user_handlers import UserHandlers
from handlers.admin_handlers import AdminHandlers

# حالات المحادثة
(
    MAIN_MENU,
    DEPOSIT_MENU,
    WITHDRAW_MENU,
    REFERRAL_MENU,
    GIFT_CODE_MENU,
    GIFT_BALANCE_MENU,
    SUPPORT_MENU,
    SETTINGS_MENU,
    ADMIN_PANEL
) = range(9)

class IChancyBot:
    def __init__(self):
        self.application = None
        self.user_handlers = UserHandlers()
        self.admin_handlers = AdminHandlers()
        self.payment_processor = PaymentProcessor()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /start"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            # التحقق إذا كان المستخدم موجوداً
            existing_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not existing_user:
                # إنشاء مستخدم جديد
                referral_code = generate_referral_code()
                new_user = User(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    referral_code=referral_code,
                    created_at=datetime.utcnow()
                )
                db.add(new_user)
                db.commit()
                
                # إرسال رسالة ترحيب للمستخدم الجديد
                welcome_message = self._get_welcome_message(new_user)
                await update.message.reply_text(welcome_message, parse_mode='HTML')
                
                # تسجيل في سجل النظام
                logger.info(f"مستخدم جديد: {user.id} - {user.username}")
            else:
                # تحديث بيانات المستخدم الحالي
                existing_user.username = user.username
                existing_user.first_name = user.first_name
                existing_user.last_name = user.last_name
                existing_user.updated_at = datetime.utcnow()
                db.commit()
            
            # عرض القائمة الرئيسية
            await self.show_main_menu(update, context, existing_user or new_user)
            
        except Exception as e:
            logger.error(f"خطأ في أمر start: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام. الرجاء المحاولة لاحقاً.")
        finally:
            db.close()
        
        return MAIN_MENU
    
    def _get_welcome_message(self, user: User) -> str:
        """رسالة ترحيب للمستخدم"""
        return f"""
🎉 <b>أهلاً وسهلاً {user.first_name}!</b>

<b>رصيدك الحالي:</b> {user.balance:,.0f} ليرة سورية
🆔 <b>رقم حسابك:</b> <code>{user.telegram_id}</code>
🔗 <b>كود الإحالة:</b> <code>{user.referral_code}</code>

📱 <b>استخدم الأزرار أدناه للتنقل:</b>
        """
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض القائمة الرئيسية"""
        keyboard = [
            [KeyboardButton("👤 Ichancy"), KeyboardButton("💳 شحن رصيد")],
            [KeyboardButton("💰 سحب رصيد"), KeyboardButton("👥 نظام الاحالات")],
            [KeyboardButton("🎁 كود هدية"), KeyboardButton("🎁 اهداء رصيد")],
            [KeyboardButton("📞 تواصل معنا"), KeyboardButton("🆘 تواصل مع الدعم")],
            [KeyboardButton("📋 السجل"), KeyboardButton("📚 الشروحات")],
            [KeyboardButton("⚡ سجل الرهانات"), KeyboardButton("⚙️ الإعدادات")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # رسالة القائمة
        menu_message = f"""
🏠 <b>القائمة الرئيسية</b>

🕐 {datetime.now().strftime("%H:%M")}
👤 <b>المستخدم:</b> {user.username or user.first_name}
💰 <b>الرصيد:</b> {user.balance:,.0f} ليرة سورية

🔽 <b>اختر من القائمة:</b>
        """
        
        if update.message:
            await update.message.reply_text(menu_message, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(menu_message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        text = update.message.text
        user_id = update.effective_user.id
        
        # التحقق من أن الرسالة ليست أمراً
        if text.startswith('/'):
            return MAIN_MENU
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text("❌ لم يتم العثور على حسابك. استخدم /start")
                return MAIN_MENU
            
            # توجيه الرسالة حسب النص
            if text == "👤 Ichancy":
                return await self.show_ichancy_menu(update, context, user)
            elif text == "💳 شحن رصيد":
                return await self.show_deposit_methods(update, context, user)
            elif text == "💰 سحب رصيد":
                return await self.show_withdraw_methods(update, context, user)
            elif text == "👥 نظام الاحالات":
                return await self.show_referral_menu(update, context, user)
            elif text == "🎁 كود هدية":
                return await self.ask_gift_code(update, context, user)
            elif text == "🎁 اهداء رصيد":
                return await self.ask_gift_recipient(update, context, user)
            elif text == "📞 تواصل معنا":
                return await self.show_contact_info(update, context, user)
            elif text == "🆘 تواصل مع الدعم":
                return await self.ask_support_message(update, context, user)
            elif text == "📋 السجل":
                return await self.show_transaction_history(update, context, user)
            elif text == "📚 الشروحات":
                return await self.show_tutorials(update, context, user)
            elif text == "⚡ سجل الرهانات":
                return await self.show_betting_history(update, context, user)
            elif text == "⚙️ الإعدادات":
                return await self.show_settings_menu(update, context, user)
            else:
                await update.message.reply_text("❌ أمر غير معروف. استخدم الأزرار أدناه.")
                return MAIN_MENU
                
        except Exception as e:
            logger.error(f"خطأ في handle_message: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام.")
            return MAIN_MENU
        finally:
            db.close()
    
    async def show_ichancy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """قائمة Ichancy"""
        db = SessionLocal()
        try:
            has_account = bool(user.ichancy_account_id)
            
            keyboard = []
            if not has_account:
                keyboard.append([InlineKeyboardButton("➕ إنشاء حساب Ichancy", callback_data="ichancy_create")])
            else:
                keyboard.append([InlineKeyboardButton("👁️ عرض معلومات الحساب", callback_data="ichancy_info")])
                keyboard.append([InlineKeyboardButton("🗑️ حذف حساب Ichancy", callback_data="ichancy_delete")])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"""
👤 <b>حساب Ichancy</b>

{'✅ لديك حساب Ichancy مرتبط' if has_account else '❌ ليس لديك حساب Ichancy'}
{'🆔 **رقم الحساب:** ' + user.ichancy_account_id if has_account else ''}
{'👤 **اسم المستخدم:** ' + user.ichancy_username if has_account else ''}

{'🔽 اختر من القائمة:' if has_account else 'لإنشاء حساب Ichancy، اضغط على الزر أدناه:'}
            """
            
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            return MAIN_MENU
            
        finally:
            db.close()
    
    async def show_deposit_methods(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """عرض طرق الشحن"""
        db = SessionLocal()
        try:
            methods = db.query(PaymentMethod).filter(
                PaymentMethod.type.in_(["deposit", "both"]),
                PaymentMethod.is_active == True
            ).all()
            
            if not methods:
                await update.message.reply_text("❌ لا توجد طرق دفع متاحة حالياً.")
                return MAIN_MENU
            
            keyboard = []
            for method in methods:
                keyboard.append([InlineKeyboardButton(
                    f"💳 {method.display_name}", 
                    callback_data=f"deposit_method_{method.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "💳 <b>اختر طريقة الدفع:</b>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return DEPOSIT_MENU
            
        finally:
            db.close()
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة Callback Queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        # توجيه الـ callback حسب البيانات
        if data == "main_menu":
            db = SessionLocal()
            user = db.query(User).filter(User.telegram_id == user_id).first()
            await self.show_main_menu(update, context, user)
            db.close()
            return MAIN_MENU
        
        elif data.startswith("deposit_method_"):
            method_id = int(data.split("_")[2])
            await self.ask_deposit_amount(update, context, method_id)
            return DEPOSIT_MENU
        
        elif data == "ichancy_create":
            await self.create_ichancy_account(update, context)
            return MAIN_MENU
        
        # ... (سيتم إكمال باقي الـ callbacks في الأجزاء القادمة)
        
        return MAIN_MENU
    
    async def ask_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, method_id: int):
        """طلب مبلغ الشحن"""
        context.user_data['deposit_method'] = method_id
        
        await update.callback_query.message.edit_text(
            "💰 <b>أدخل المبلغ المراد شحنه:</b>\n"
            "📝 <i>الحد الأدنى: 500 ليرة | الحد الأقصى: 50,000 ليرة</i>",
            parse_mode='HTML'
        )
        return DEPOSIT_MENU
    
    async def create_ichancy_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء حساب Ichancy"""
        user_id = update.callback_query.from_user.id
        db = SessionLocal()
        
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.callback_query.message.edit_text("❌ لم يتم العثور على حسابك.")
                return MAIN_MENU
            
            if user.ichancy_account_id:
                await update.callback_query.message.edit_text("✅ لديك حساب Ichancy مسبقاً.")
                return MAIN_MENU
            
            # هنا سيتم استدعاء الـ Webhook لإنشاء الحساب
            # مؤقتاً: إنشاء حساب وهمي
            import random
            import string
            
            account_id = ''.join(random.choices(string.digits, k=8))
            username = f"{user.first_name}_{random.randint(1000, 9999)}"
            
            user.ichancy_account_id = account_id
            user.ichancy_username = username
            db.commit()
            
            await update.callback_query.message.edit_text(
                f"✅ <b>تم إنشاء حساب Ichancy بنجاح!</b>\n\n"
                f"🆔 <b>رقم الحساب:</b> <code>{account_id}</code>\n"
                f"👤 <b>اسم المستخدم:</b> <code>{username}</code>\n"
                f"🔒 <b>كلمة السر:</b> <code>{''.join(random.choices(string.ascii_letters + string.digits, k=8))}</code>\n\n"
                f"⚠️ <i>احتفظ بهذه المعلومات في مكان آمن.</i>",
                parse_mode='HTML'
            )
            
            # إرسال إشعار للإدمن
            await self._notify_admins(
                f"📝 <b>حساب Ichancy جديد</b>\n"
                f"👤 المستخدم: {user.username or user.first_name}\n"
                f"🆔 رقم الحساب: {account_id}",
                context
            )
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء حساب Ichancy: {e}")
            await update.callback_query.message.edit_text("❌ فشل في إنشاء الحساب. حاول لاحقاً.")
        finally:
            db.close()
    
    async def _notify_admins(self, message: str, context: ContextTypes.DEFAULT_TYPE):
        """إرسال إشعار للإدمن"""
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"فشل إرسال إشعار للإدمن {admin_id}: {e}")
    
    def run(self):
        """تشغيل البوت"""
        # إنشاء التطبيق
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # إضافة Handlers
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                MAIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
                    CallbackQueryHandler(self.callback_handler)
                ],
                DEPOSIT_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_deposit_amount),
                    CallbackQueryHandler(self.callback_handler)
                ],
                # ... (سيتم إضافة باقي الـ states)
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
        
        # تشغيل البوت
        logger.info("🤖 بدء تشغيل البوت...")
        self.application.run_polling(allowed_updates=Update.ALL_UPDATES)
    
    async def process_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة مبلغ الشحن"""
        try:
            amount = float(update.message.text)
            
            if amount < Config.MIN_DEPOSIT or amount > Config.MAX_DEPOSIT:
                await update.message.reply_text(
                    f"❌ المبلغ خارج النطاق المسموح.\n"
                    f"الحد الأدنى: {Config.MIN_DEPOSIT:,} ليرة\n"
                    f"الحد الأقصى: {Config.MAX_DEPOSIT:,} ليرة"
                )
                return DEPOSIT_MENU
            
            method_id = context.user_data.get('deposit_method')
            if not method_id:
                await update.message.reply_text("❌ لم يتم اختيار طريقة دفع.")
                return MAIN_MENU
            
            # حفظ المبلغ مؤقتاً
            context.user_data['deposit_amount'] = amount
            
            db = SessionLocal()
            method = db.query(PaymentMethod).filter(PaymentMethod.id == method_id).first()
            db.close()
            
            if not method:
                await update.message.reply_text("❌ طريقة الدفع غير موجودة.")
                return MAIN_MENU
            
            # بناء على طريقة الدفع، نطلب معلومات إضافية
            if method.name == "syriatel_cash":
                await self.process_syriatel_deposit(update, context, method, amount)
            elif method.name == "cham_cash":
                await self.process_cham_dash_deposit(update, context, method, amount)
            else:
                await self.process_generic_deposit(update, context, method, amount)
            
            return DEPOSIT_MENU
            
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح.")
            return DEPOSIT_MENU
        except Exception as e:
            logger.error(f"خطأ في process_deposit_amount: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام.")
            return MAIN_MENU
    
    async def process_syriatel_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, method: PaymentMethod, amount: float):
        """معالجة شحن سيرياتيل كاش"""
        # البحث عن كود سيرياتيل مناسب
        db = SessionLocal()
        try:
            # البحث عن كود متاح
            available_code = db.query(SyriatelCode).filter(
                SyriatelCode.is_active == True,
                SyriatelCode.max_balance - SyriatelCode.current_balance >= amount
            ).first()
            
            if not available_code:
                await update.message.reply_text(
                    "❌ لا توجد أكواد سيرياتيل متاحة لهذا المبلغ حالياً.\n"
                    "الرجاء المحاولة لاحقاً أو اختيار طريقة دفع أخرى."
                )
                return
            
            # عرض الكود للمستخدم
            message = f"""
💳 <b>تفاصيل التحويل - سيرياتيل كاش</b>

💰 <b>المبلغ:</b> {amount:,.0f} ليرة سورية
🔢 <b>كود السيرياتيل:</b> <code>{available_code.code}</code>

📋 <b>تعليمات:</b>
1. قم بتحويل المبلغ إلى الرقم أعلاه
2. احفظ <b>رقم العملية</b>
3. أرسل رقم العملية هنا

⚠️ <i>يجب أن يتم التحويل خلال 15 دقيقة</i>
            """
            
            # حفظ الكود في السياق
            context.user_data['syriatel_code'] = available_code.code
            context.user_data['syriatel_code_id'] = available_code.id
            
            await update.message.reply_text(message, parse_mode='HTML')
            
            # تحديث الكود بأنه قيد الاستخدام
            available_code.current_balance += amount
            db.commit()
            
        finally:
            db.close()
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء العملية الحالية"""
        await update.message.reply_text(
            "تم الإلغاء. استخدم /start للبدء من جديد.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# نقطة الدخول الرئيسية
if __name__ == "__main__":
    bot = IChancyBot()
    bot.run()