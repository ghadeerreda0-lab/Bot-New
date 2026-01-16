"""
معالجات الأدمن
"""

import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService
from services.payment_service import PaymentService
from services.ichancy_service import IchancyService
from services.referral_service import ReferralService
from services.gift_service import GiftService
from services.transaction_service import TransactionService
from keyboards.admin_keyboards import (
    admin_panel_keyboard,
    general_settings_keyboard,
    payment_settings_keyboard,
    withdraw_settings_keyboard,
    users_management_keyboard,
    referral_settings_keyboard,
    ichancy_settings_keyboard,
    reports_keyboard,
    manage_admins_keyboard,
    confirmation_keyboard
)

logger = logging.getLogger(__name__)

def register_admin_handlers(bot: TeleBot, user_service: UserService, 
                           payment_service: PaymentService,
                           ichancy_service: IchancyService,
                           referral_service: ReferralService,
                           gift_service: GiftService,
                           transaction_service: TransactionService):
    """تسجيل جميع معالجات الأدمن"""
    
    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        """فتح لوحة تحكم الأدمن"""
        user_id = message.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.reply_to(message, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "🎛 **لوحة تحكم الإدمن**\n\nاختر القسم الذي تريد إدارته:",
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ خطأ في فتح لوحة الأدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def admin_panel_callback(call):
        """فتح لوحة التحكم من الكال باك"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "🎛 **لوحة تحكم الإدمن**\n\nاختر القسم الذي تريد إدارته:",
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في فتح لوحة الأدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_back_to_panel")
    def back_to_admin_panel(call):
        """العودة للوحة التحكم"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "🎛 **لوحة تحكم الإدمن**\n\nاختر القسم الذي تريد إدارته:",
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في العودة للوحة الأدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_general_settings")
    def general_settings(call):
        """الإعدادات العامة"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "⚙️ **الإعدادات العامة**\n\nإدارة جميع إعدادات النظام:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=general_settings_keyboard(payment_service),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض الإعدادات العامة: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_toggle_"))
    def toggle_setting(call):
        """تبديل إعداد"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        setting_map = {
            "admin_toggle_ichancy": "ichancy_enabled",
            "admin_toggle_ichancy_create": "ichancy_create_account_enabled",
            "admin_toggle_ichancy_deposit": "ichancy_deposit_enabled",
            "admin_toggle_ichancy_withdraw": "ichancy_withdraw_enabled",
            "admin_toggle_deposit": "deposit_enabled",
            "admin_toggle_withdraw": "withdraw_enabled",
            "admin_toggle_withdraw_button": "withdraw_button_visible",
            "admin_toggle_maintenance": "maintenance_mode"
        }
        
        if call.data in setting_map:
            setting_key = setting_map[call.data]
            current = payment_service.get_setting(setting_key) == 'true'
            new_value = 'false' if current else 'true'
            
            success = payment_service.update_setting(setting_key, new_value, user_id)
            
            if success:
                status = "مفعل" if new_value == 'true' else "معطل"
                if call.data == "admin_toggle_withdraw_button":
                    status = "مرئي" if new_value == 'true' else "مخفي"
                
                bot.answer_callback_query(call.id, f"✅ أصبح: {status}")
                
                # تحديث الواجهة
                try:
                    if "ichancy" in call.data:
                        bot.edit_message_reply_markup(
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=ichancy_settings_keyboard(payment_service)
                        )
                    elif "withdraw" in call.data:
                        bot.edit_message_reply_markup(
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=withdraw_settings_keyboard(payment_service)
                        )
                    else:
                        bot.edit_message_reply_markup(
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=general_settings_keyboard(payment_service)
                        )
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ فشل التحديث")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_payment_settings")
    def payment_settings(call):
        """إعدادات الدفع"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "💰 **إعدادات الدفع**\n\nإدارة جميع طرق الدفع:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=payment_settings_keyboard(payment_service),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إعدادات الدفع: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw_settings")
    def withdraw_settings(call):
        """إعدادات السحب"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "💸 **إعدادات السحب**\n\nإدارة جميع إعدادات نظام السحب:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=withdraw_settings_keyboard(payment_service),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إعدادات السحب: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_edit_withdraw_percentage")
    def edit_withdraw_percentage(call):
        """تعديل نسبة السحب"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "📊 **تعديل نسبة السحب**\n\n"
                "أدخل نسبة السحب (0-100):\n"
                "0 يعني بدون نسبة خصم\n"
                "مثال: 10 ← نسبة 10%"
            )
            bot.answer_callback_query(call.id)
            # Note: Need to handle the response in message handler
        except Exception as e:
            logger.error(f"❌ خطأ في طلب نسبة السحب: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_users_management")
    def users_management(call):
        """إدارة المستخدمين"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "👥 **إدارة المستخدمين**\n\nاختر الإجراء المطلوب:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=users_management_keyboard(),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إدارة المستخدمين: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_users_count")
    def users_count(call):
        """عدد المستخدمين"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            stats = user_service.get_users_count()
            
            message = (
                f"👥 **إحصائيات المستخدمين**\n\n"
                f"📊 **إجمالي المستخدمين:** {stats['total']}\n"
                f"🚫 **المحظورين:** {stats['banned']}\n"
                f"✅ **النشطين:** {stats['active']}\n\n"
                f"📈 **آخر 5 مستخدمين جدد:**\n"
            )
            
            users = user_service.get_all_users(limit=5)
            for user in users:
                user_id, balance, created_at, last_active, is_banned = user
                message += f"• `{user_id}` - {balance:,} ليرة - {created_at[:10]}\n"
            
            bot.send_message(user_id, message, parse_mode="Markdown")
            bot.answer_callback_query(call.id, f"✅ العدد: {stats['total']}")
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عدد المستخدمين: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في الجلب")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
    def add_balance(call):
        """إضافة رصيد لمستخدم"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "💰 **إضافة رصيد لمستخدم**\n\n"
                "أدخل ID المستخدم:"
            )
            bot.answer_callback_query(call.id)
            # Note: Need to handle the response in message handler
        except Exception as e:
            logger.error(f"❌ خطأ في طلب إضافة رصيد: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_edit_gift_percentage")
    def edit_gift_percentage(call):
        """تعديل نسبة الإهداء"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "🎁 **تعديل نسبة الإهداء**\n\n"
                "أدخل نسبة الإهداء (0-100):\n"
                "0 يعني بدون نسبة خصم\n"
                "مثال: 5 ← نسبة 5% على المبلغ المُهدى"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب نسبة الإهداء: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_top_balance")
    def top_balance(call):
        """أعلى رصيد مستخدمين"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "🏆 **أعلى رصيد مستخدمين**\n\n"
                "أدخل عدد المستخدمين المطلوب عرضهم (مثال: 20):"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب أعلى الرصيد: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_reset_all_balances")
    def reset_all_balances(call):
        """تصفير جميع الأرصدة"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            kb = confirmation_keyboard("reset_balances", "all")
            bot.edit_message_text(
                "⚠️ **تصفير جميع الأرصدة**\n\n"
                "هل أنت متأكد أنك تريد تصفير أرصدة جميع المستخدمين؟\n"
                "هذا الإجراء لا يمكن التراجع عنه!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب تصفير الأرصدة: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "confirm_reset_balances_all")
    def confirm_reset_balances(call):
        """تأكيد تصفير الأرصدة"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            result = user_service.reset_all_balances()
            if result['success']:
                message = f"✅ تم تصفير أرصدة {result.get('affected', 0)} مستخدم"
            else:
                message = f"❌ خطأ: {result.get('message', 'غير معروف')}"
            
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id, message)
        except Exception as e:
            logger.error(f"❌ خطأ في تصفير الأرصدة: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_referral_settings")
    def referral_settings_menu(call):
        """إعدادات الإحالات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "🤝 **إعدادات الإحالات**\n\nإدارة نظام الإحالات والمكافآت:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=referral_settings_keyboard(referral_service),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إعدادات الإحالات: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_edit_referral_rate")
    def edit_referral_rate(call):
        """تعديل نسبة الإحالات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "📊 **تعديل نسبة الإحالات**\n\n"
                "أدخل نسبة العمولة (0-100):\n"
                "0 يعني بدون عمولة\n"
                "مثال: 10 ← نسبة 10% من الشحن"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب نسبة الإحالات: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_top_referrals")
    def top_referrals(call):
        """أعلى الإحالات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "📈 **أعلى الإحالات**\n\n"
                "أدخل عدد الإحالات المطلوب عرضهم (مثال: 15):"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب أعلى الإحالات: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_distribute_referrals")
    def distribute_referrals(call):
        """توزيع عمولات الإحالات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            result = referral_service.distribute_referral_commissions()
            bot.answer_callback_query(call.id, result['message'])
        except Exception as e:
            logger.error(f"❌ خطأ في توزيع الإحالات: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_ichancy_settings")
    def ichancy_settings_menu(call):
        """إعدادات Ichancy"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "⚡ **إعدادات نظام Ichancy**\n\nإدارة نظام Ichancy بالكامل:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=ichancy_settings_keyboard(payment_service),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إعدادات Ichancy: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_reports")
    def reports_menu(call):
        """التقارير والإحصائيات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "📊 **التقارير والإحصائيات**\n\nاختر نوع التقرير:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=reports_keyboard(),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض التقارير: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "report_today")
    def report_today(call):
        """تقرير اليوم"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            report = payment_service.get_daily_report()
            if not report:
                bot.answer_callback_query(call.id, "❌ فشل في جلب التقرير")
                return
            
            message = (
                f"📊 **تقرير اليوم - {report['date']}**\n\n"
                f"👥 **المستخدمون:**\n"
                f"• 👤 مستخدمين جدد: {report['new_users']}\n"
                f"• 📊 الإجمالي: {report['total_users']}\n"
                f"• 🎯 النشطين: {report['active_users']}\n\n"
                f"💰 **الأداء المالي:**\n"
                f"• 💳 إجمالي الإيداع: {report['total_deposit']:,} ليرة\n"
                f"• 💸 إجمالي السحب: {report['total_withdraw']:,} ليرة\n"
                f"• 📈 صافي التدفق: {report['net_flow']:,} ليرة\n"
                f"• 📋 المعاملات: {report['total_transactions']}\n"
                f"• ⏳ المعلقة: {report['pending_transactions']}\n\n"
                f"🤝 **الإحالات:**\n"
                f"• 👥 إحالات جديدة: {report['new_referrals']}\n\n"
                f"📱 **أكواد سيرياتيل:**\n"
                f"• 🔢 عدد الأكواد: {report['active_codes']}\n"
                f"• 💰 المستخدم: {report['used_capacity']:,} ليرة\n"
                f"• 📊 السعة: {report['total_capacity']:,} ليرة\n"
                f"• 📈 النسبة: {report['fill_percentage']}%\n\n"
                f"🕒 **التاريخ:** {report['date']} {call.message.date}"
            )
            
            bot.send_message(user_id, message, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ تم إرسال التقرير")
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تقرير اليوم: {e}")
            bot.answer_callback_query(call.id, "❌ فشل في الجلب")
    
    @bot.callback_query_handler(func=lambda call: call.data == "report_deposit")
    def report_deposit_menu(call):
        """قائمة تقارير الشحن"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            kb = InlineKeyboardMarkup(row_width=2)
            kb.row(
                InlineKeyboardButton("📱 سيرياتيل كاش", callback_data="report_deposit_syriatel"),
                InlineKeyboardButton("💰 شام كاش", callback_data="report_deposit_sham")
            )
            kb.row(
                InlineKeyboardButton("💵 شام دولار", callback_data="report_deposit_sham_usd"),
                InlineKeyboardButton("📊 جميع الطرق", callback_data="report_deposit_all")
            )
            kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_reports"))
            
            bot.edit_message_text(
                "💰 **تقرير عمليات الشحن**\n\nاختر طريقة الدفع:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض تقارير الشحن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("report_deposit_"))
    def report_deposit(call):
        """تقرير عمليات الشحن"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        method_map = {
            "report_deposit_syriatel": "سيرياتيل كاش",
            "report_deposit_sham": "شام كاش",
            "report_deposit_sham_usd": "شام كاش دولار",
            "report_deposit_all": None
        }
        
        if call.data in method_map:
            method_name = method_map[call.data]
            report = payment_service.get_deposit_report(method_name)
            
            if not report:
                bot.answer_callback_query(call.id, "❌ فشل في جلب التقرير")
                return
            
            message = (
                f"💳 **تقرير الشحن - {report['date']}**\n\n"
                f"📱 **الطريقة:** {report['payment_method']}\n"
                f"💰 **إجمالي المبلغ:** {report['total_amount']:,} ليرة\n"
                f"📋 **عدد العمليات:** {report['total_count']}\n\n"
            )
            
            if report['transactions']:
                message += "📅 **آخر 10 عمليات:**\n\n"
                for tx in report['transactions'][:10]:
                    tx_id, user_id_tx, amount, method, created_at, status, user_balance = tx
                    status_icon = "✅" if status == 'approved' else "⏳" if status == 'pending' else "❌"
                    message += f"{status_icon} **{created_at}**\n"
                    message += f"👤 المستخدم: `{user_id_tx}`\n"
                    message += f"💰 المبلغ: {amount:,} ليرة\n"
                    message += f"💳 الرصيد: {user_balance:,} ليرة\n"
                    message += f"🆔 العملية: #{tx_id}\n"
                    message += "─" * 20 + "\n"
            else:
                message += "❌ لا توجد عمليات شحن لهذا اليوم\n"
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅ ↩️ رجوع للتقارير", callback_data="admin_reports"))
            
            bot.send_message(user_id, message[:4000], parse_mode="Markdown", reply_markup=kb)
            bot.answer_callback_query(call.id, "✅ تم إرسال التقرير")
    
    @bot.callback_query_handler(func=lambda call: call.data == "report_withdraw")
    def report_withdraw(call):
        """تقرير عمليات السحب"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            report = payment_service.get_withdraw_report()
            if not report:
                bot.answer_callback_query(call.id, "❌ فشل في جلب التقرير")
                return
            
            message = (
                f"💸 **تقرير السحب - {report['date']}**\n\n"
                f"💰 **إجمالي المبلغ:** {report['total_amount']:,} ليرة\n"
                f"📋 **عدد العمليات:** {report['total_count']}\n\n"
            )
            
            if report['transactions']:
                message += "📅 **آخر 10 عمليات:**\n\n"
                for tx in report['transactions'][:10]:
                    tx_id, user_id_tx, amount, method, created_at, status, user_balance = tx
                    status_icon = "✅" if status == 'approved' else "⏳" if status == 'pending' else "❌"
                    message += f"{status_icon} **{created_at}**\n"
                    message += f"👤 المستخدم: `{user_id_tx}`\n"
                    message += f"💰 المبلغ: {amount:,} ليرة\n"
                    message += f"💳 الرصيد: {user_balance:,} ليرة\n"
                    message += f"🆔 العملية: #{tx_id}\n"
                    message += "─" * 20 + "\n"
            else:
                message += "❌ لا توجد عمليات سحب لهذا اليوم\n"
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⬅ ↩️ رجوع للتقارير", callback_data="admin_reports"))
            
            bot.send_message(user_id, message[:4000], parse_mode="Markdown", reply_markup=kb)
            bot.answer_callback_query(call.id, "✅ تم إرسال التقرير")
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تقرير السحب: {e}")
            bot.answer_callback_query(call.id, "❌ فشل في الجلب")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_manage_admins")
    def manage_admins(call):
        """إدارة الأدمن"""
        user_id = call.from_user.id
        
        if not user_service.can_manage_admins(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.edit_message_text(
                "👑 **إدارة الأدمن**\n\nإضافة وحذف الأدمن الثانويين:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=manage_admins_keyboard(),
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض إدارة الأدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_admin")
    def add_admin_menu(call):
        """إضافة أدمن"""
        user_id = call.from_user.id
        
        if not user_service.can_manage_admins(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "➕ **إضافة أدمن جديد**\n\n"
                "أدخل ID المستخدم المراد ترقيته لأدمن:"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب إضافة أدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_remove_admin")
    def remove_admin_menu(call):
        """حذف أدمن"""
        user_id = call.from_user.id
        
        if not user_service.can_manage_admins(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            bot.send_message(
                user_id,
                "🗑️ **حذف أدمن**\n\n"
                "أدخل ID الأدمن المراد حذفه:"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في طلب حذف أدمن: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_list_admins")
    def list_admins(call):
        """عرض جميع الأدمن"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
            return
        
        try:
            admins = user_service.get_all_admins()
            if not admins:
                bot.answer_callback_query(call.id, "❌ لا توجد أدمن ثانويين")
                return
            
            message = "👑 **قائمة الأدمن الثانويين:**\n\n"
            
            for admin in admins:
                admin_id, created_at, added_at, added_by = admin
                message += f"👤 **المستخدم:** `{admin_id}`\n"
                message += f"📅 انضم للبوت: {created_at[:10]}\n"
                message += f"👑 أصبح أدمن: {added_at[:10]}\n"
                message += f"➕ تمت الإضافة بواسطة: `{added_by}`\n"
                message += "─" * 20 + "\n"
            
            message += f"\n📊 **المجموع:** {len(admins)} أدمن ثانوي"
            
            bot.send_message(user_id, message, parse_mode="Markdown")
            bot.answer_callback_query(call.id, f"✅ عدد الأدمن: {len(admins)}")
        except Exception as e:
            logger.error(f"❌ خطأ في جلب قائمة الأدمن: {e}")
            bot.answer_callback_query(call.id, "❌ فشل في الجلب")
    
    logger.info("✅ تم تسجيل معالجات الأدمن")