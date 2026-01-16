"""
معالجات المستخدمين العاديين
"""

import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService
from services.payment_service import PaymentService
from services.ichancy_service import IchancyService
from services.referral_service import ReferralService
from services.gift_service import GiftService
from keyboards.user_keyboards import (
    main_menu_keyboard,
    deposit_menu_keyboard,
    user_logs_keyboard,
    ichancy_menu_keyboard
)

logger = logging.getLogger(__name__)

def register_user_handlers(bot: TeleBot, user_service: UserService, 
                          payment_service: PaymentService, 
                          ichancy_service: IchancyService,
                          referral_service: ReferralService,
                          gift_service: GiftService):
    """تسجيل جميع معالجات المستخدمين"""
    
    @bot.message_handler(commands=['start'])
    def start_command(message):
        """معالجة أمر /start"""
        user_id = message.from_user.id
        
        try:
            # التحقق من وضع الصيانة
            maintenance_mode = payment_service.get_setting('maintenance_mode') == 'true'
            if maintenance_mode and not user_service.is_admin(user_id):
                maintenance_msg = payment_service.get_setting('maintenance_message', 
                                                            '🔧 البوت تحت الصيانة حاليًا.')
                bot.send_message(user_id, maintenance_msg)
                return
            
            # إنشاء المستخدم إذا لم يكن موجوداً
            user_service.create_user(user_id)
            
            # التحقق من الحظر
            user_data = user_service.get_user(user_id)
            if user_data and user_data['is_banned']:
                ban_reason = user_data['ban_reason'] or "غير محدد"
                ban_until = user_data['ban_until'] or "غير محدد"
                bot.send_message(
                    user_id,
                    f"🚫 **حسابك محظور!**\n\n"
                    f"📝 السبب: {ban_reason}\n"
                    f"⏰ حتى: {ban_until}\n\n"
                    f"للمساعدة راسل الدعم."
                )
                return
            
            # إرسال رسالة الترحيب
            balance = user_data['balance'] if user_data else 0
            welcome_template = payment_service.get_setting('welcome_message')
            if not welcome_template:
                welcome_template = "👋 أهلاً بك!\nرصيدك الحالي: {balance} ليرة سورية"
            
            welcome_msg = welcome_template.format(balance=balance)
            bot.send_message(user_id, welcome_msg, reply_markup=main_menu_keyboard(user_id, ichancy_service))
            
            # مسح الجلسة القديمة
            # Note: Need session service
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة /start: {e}")
            bot.send_message(user_id, "❌ حدث خطأ، حاول مرة أخرى")
    
    @bot.callback_query_handler(func=lambda call: call.data == "back")
    def back_to_main(call):
        """العودة للقائمة الرئيسية"""
        user_id = call.from_user.id
        try:
            bot.edit_message_text(
                "✅ عدنا إلى القائمة الرئيسية:",
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=main_menu_keyboard(user_id, ichancy_service)
            )
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة back: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "deposit_menu")
    def deposit_menu(call):
        """قائمة طرق الشحن"""
        user_id = call.from_user.id
        
        # التحقق من تفعيل الشحن
        deposit_enabled = payment_service.get_setting('deposit_enabled') == 'true'
        if not deposit_enabled and not user_service.is_admin(user_id):
            deposit_msg = payment_service.get_setting('deposit_message', 
                                                    '💰 نظام الشحن معطل حالياً')
            bot.answer_callback_query(call.id, deposit_msg)
            return
        
        try:
            bot.edit_message_text(
                "💰 **اختر طريقة الشحن:**",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=deposit_menu_keyboard(payment_service)
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض قائمة الشحن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "ichancy_info")
    def ichancy_info(call):
        """معلومات حساب Ichancy"""
        user_id = call.from_user.id
        
        # التحقق من تفعيل Ichancy
        ichancy_enabled = payment_service.get_setting('ichancy_enabled') == 'true'
        if not ichancy_enabled:
            bot.answer_callback_query(call.id, "❌ نظام Ichancy معطل حالياً")
            return
        
        try:
            account = ichancy_service.get_ichancy_account(user_id)
            
            if account:
                message_text = (
                    f"⚡ **معلومات حساب Ichancy**\n\n"
                    f"👤 **اسم المستخدم:** `{account['username']}`\n"
                    f"🔑 **كلمة المرور:** `{account['password']}`\n"
                    f"💰 **الرصيد:** {account['balance']:,} ليرة\n"
                    f"📅 **تاريخ الإنشاء:** {account['created_at']}\n"
                    f"🔐 **آخر دخول:** {account['last_login'] or 'لم يسجل دخول بعد'}\n\n"
                    f"*احتفظ ببيانات حسابك في مكان آمن!*"
                )
                
                kb = ichancy_menu_keyboard(has_account=True)
                bot.edit_message_text(
                    message_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            else:
                # عرض خيار إنشاء حساب
                create_enabled = payment_service.get_setting('ichancy_create_account_enabled') == 'true'
                if not create_enabled:
                    bot.answer_callback_query(call.id, "❌ إنشاء حسابات Ichancy معطل حالياً")
                    return
                
                message_text = (
                    "⚡ **نظام Ichancy**\n\n"
                    "ليس لديك حساب Ichancy بعد.\n"
                    "يمكنك إنشاء حساب جديد للاستفادة من خدمات Ichancy المتكاملة."
                )
                
                kb = ichancy_menu_keyboard(has_account=False)
                bot.edit_message_text(
                    message_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض معلومات Ichancy: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data == "ichancy_create")
    def ichancy_create(call):
        """إنشاء حساب Ichancy"""
        user_id = call.from_user.id
        
        # التحقق من تفعيل إنشاء الحساب
        create_enabled = payment_service.get_setting('ichancy_create_account_enabled') == 'true'
        if not create_enabled:
            bot.answer_callback_query(call.id, "❌ إنشاء حسابات Ichancy معطل حالياً")
            return
        
        try:
            result = ichancy_service.create_ichancy_account(user_id)
            
            if result['success']:
                message_text = (
                    f"✅ **تم إنشاء حساب Ichancy بنجاح!**\n\n"
                    f"👤 **اسم المستخدم:** `{result['username']}`\n"
                    f"🔑 **كلمة المرور:** `{result['password']}`\n\n"
                    f"💰 **الرصيد الابتدائي:** 0 ليرة\n\n"
                    f"⚠️ **احتفظ ببيانات حسابك في مكان آمن!**\n"
                    f"*يمكنك الآن استخدام جميع خدمات Ichancy*"
                )
                
                kb = ichancy_menu_keyboard(has_account=True)
                bot.edit_message_text(
                    message_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, result['message'])
            
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء حساب Ichancy: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data == "user_logs")
    def user_logs_menu(call):
        """قائمة سجل المستخدم"""
        try:
            bot.edit_message_text(
                "📜 **سجلك الشخصي**\n\n"
                "اختر نوع السجل الذي تريد عرضه:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=user_logs_keyboard()
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض سجل المستخدم: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "referrals")
    def referrals_menu(call):
        """نظام الإحالات"""
        user_id = call.from_user.id
        
        try:
            user_data = user_service.get_user(user_id)
            if not user_data:
                bot.answer_callback_query(call.id, "❌ خطأ في جلب البيانات")
                return
            
            referrals = referral_service.get_user_referrals(user_id)
            settings = referral_service.get_referral_settings()
            
            message = "🤝 **نظام الإحالات**\n\n"
            
            # معلومات النظام
            if settings:
                message += f"📊 **النظام الأول:**\n"
                message += f"• نسبة الربح: {settings.get('commission_rate', 10)}% من رابط الإحالة\n"
                message += f"• شروط الحصول:\n"
                message += f"  - {settings.get('min_active_referrals', 5)} إحالات نشطة على الأقل\n"
                message += f"  - إحالة واحدة على الأقل بحرق {settings.get('min_charge_amount', 100000):,}+ ليرة\n\n"
                
                message += f"💰 **النظام الثاني:**\n"
                message += f"• مكافأة: {settings.get('bonus_amount', 2000):,} ليرة لكل إحالة نشطة\n"
                message += f"• قامت بشحن 10,000+ ليرة (أي عملة)\n\n"
                
                next_dist = settings.get('next_distribution')
                if next_dist:
                    message += f"⏰ **موعد توزيع الجوائز القادم:**\n"
                    message += f"{next_dist}\n\n"
            
            # رابط الإحالة
            referral_code = user_data.get('referral_code')
            if referral_code:
                bot_username = bot.get_me().username
                message += f"🔗 **رابط إحالتك:**\n"
                message += f"`https://t.me/{bot_username}?start=ref_{referral_code}`\n\n"
            
            # إحصائيات المستخدم
            total_refs = len(referrals)
            active_refs = sum(1 for r in referrals if r[3])  # r[3] هو is_active
            
            message += f"📈 **إحصائياتك:**\n"
            message += f"• عدد إحالاتك: {total_refs}\n"
            message += f"• الإحالات النشطة: {active_refs}\n"
            
            # حساب الأرباح المستحقة (مبسط)
            if settings and active_refs >= settings.get('min_active_referrals', 5):
                eligible_refs = [r for r in referrals if r[2] >= settings.get('min_charge_amount', 100000)]
                if eligible_refs:
                    total_charged = sum(r[2] for r in eligible_refs)
                    commission = total_charged * (settings.get('commission_rate', 10) / 100)
                    bonus = len(eligible_refs) * settings.get('bonus_amount', 2000)
                    total_commission = commission + bonus
                    
                    message += f"• 💰 الأرباح المستحقة: {int(total_commission):,} ليرة\n"
            
            message += f"\n*لزيادة فرصك في الحصول على المكافآت، شارك رابط الإحالة الخاص بك مع أصدقائك!*"
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="back"))
            
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض نظام الإحالات: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data == "gift_balance")
    def gift_balance(call):
        """إهداء رصيد"""
        user_id = call.from_user.id
        
        try:
            # حفظ الجلسة للانتقال للخطوة التالية
            # Note: Need session service
            
            bot.edit_message_text(
                "🎁 **إهداء رصيد**\n\n"
                "أدخل المبلغ الذي تريد إهداءه:",
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في بدء عملية الإهداء: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "gift_code")
    def gift_code_input(call):
        """إدخال كود الهدية"""
        try:
            bot.edit_message_text(
                "🎁 **تفعيل كود هدية**\n\n"
                "أدخل كود الهدية:",
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب كود الهدية: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "withdraw")
    def withdraw_menu(call):
        """قائمة السحب"""
        user_id = call.from_user.id
        
        # التحقق من تفعيل السحب
        withdraw_enabled = payment_service.get_setting('withdraw_enabled') == 'true'
        if not withdraw_enabled:
            withdraw_msg = payment_service.get_setting('withdraw_message', 
                                                      '💸 نظام السحب معطل حالياً')
            bot.answer_callback_query(call.id, withdraw_msg)
            return
        
        # التحقق من إظهار زر السحب
        withdraw_visible = payment_service.get_setting('withdraw_button_visible') == 'true'
        if not withdraw_visible:
            bot.answer_callback_query(call.id, "❌ خدمة السحب غير متوفرة حالياً")
            return
        
        try:
            withdraw_percentage = int(payment_service.get_setting('withdraw_percentage', '0'))
            message = "💸 **سحب رصيد**\n\n"
            
            if withdraw_percentage > 0:
                message += f"📊 **نسبة السحب:** {withdraw_percentage}%\n"
                message += f"*سيتم خصم {withdraw_percentage}% من المبلغ المسحوب*\n\n"
            
            message += "💰 أدخل المبلغ المراد سحبه:"
            
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض قائمة السحب: {e}")
    
    # باقي معالجات المستخدمين سيتم إضافتها في ملفات منفصلة
    
    logger.info("✅ تم تسجيل معالجات المستخدمين")