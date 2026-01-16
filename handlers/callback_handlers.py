"""
معالجات الكال باك (Callback Query Handlers)
"""

import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService
from services.payment_service import PaymentService
from services.transaction_service import TransactionService
from services.gift_service import GiftService
from keyboards.admin_keyboards import transaction_approval_keyboard

logger = logging.getLogger(__name__)

def register_callback_handlers(bot: TeleBot, user_service: UserService,
                              payment_service: PaymentService,
                              transaction_service: TransactionService,
                              gift_service: GiftService):
    """تسجيل جميع معالجات الكال باك"""
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
    def handle_transaction_approval(call):
        """معالجة الموافقة/الرفض على المعاملات"""
        user_id = call.from_user.id
        
        if not user_service.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
            return
        
        try:
            data = call.data
            action, tx_id_str = data.split("_", 1)
            tx_id = int(tx_id_str)
            
            if action == "approve":
                result = transaction_service.approve_transaction(tx_id, user_id)
                status_text = "✅ مقبول"
            else:
                result = transaction_service.reject_transaction(tx_id, user_id)
                status_text = "❌ مرفوض"
            
            if result['success']:
                # تحديث الرسالة الأصلية
                try:
                    current_text = call.message.text
                    new_text = current_text + f"\n\n{status_text}\n👤 المعالج: {user_id}"
                    
                    bot.edit_message_text(
                        new_text,
                        call.message.chat.id,
                        call.message.message_id
                    )
                except:
                    pass
                
                # إرسال إشعار للمستخدم
                if 'notification' in result:
                    try:
                        bot.send_message(
                            result['user_id'],
                            result['notification']
                        )
                    except:
                        pass
                
                bot.answer_callback_query(call.id, result['message'])
            else:
                bot.answer_callback_query(call.id, result['message'])
                
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الموافقة: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في المعالجة")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
    def handle_payment_method(call):
        """معالجة اختيار طريقة الدفع"""
        user_id = call.from_user.id
        
        try:
            method = call.data.replace("pay_", "")
            
            # التحقق من تفعيل طريقة الدفع
            if not payment_service.check_payment_enabled(method):
                bot.answer_callback_query(call.id, "❌ طريقة الدفع غير متاحة حالياً")
                return
            
            methods = payment_service.get_payment_methods()
            method_info = methods.get(method)
            
            if not method_info:
                bot.answer_callback_query(call.id, "❌ طريقة دفع غير معروفة")
                return
            
            method_name = method_info['name']
            min_amount = method_info['min_amount']
            max_amount = method_info['max_amount']
            
            message = f"💰 **{method_name}**\n\n"
            message += f"📊 **الحدود المسموحة:**\n"
            
            if method == 'sham_cash_usd':
                message += f"• الحد الأدنى: {min_amount:,} دولار\n"
                message += f"• الحد الأقصى: {max_amount:,} دولار\n\n"
                message += f"💸 أدخل المبلغ بالدولار:"
            else:
                message += f"• الحد الأدنى: {min_amount:,} ليرة\n"
                message += f"• الحد الأقصى: {max_amount:,} ليرة\n\n"
                message += f"💸 أدخل المبلغ بالليرة السورية:"
            
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)
            
            # Note: Need session service to store the selected method
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة طريقة الدفع: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_gift_"))
    def confirm_gift(call):
        """تأكيد عملية الإهداء"""
        user_id = call.from_user.id
        
        try:
            # استخراج البيانات من الكال باك
            parts = call.data.split("_")
            if len(parts) >= 4:
                receiver_id = int(parts[2])
                amount = int(parts[3])
                
                # جلب نسبة الإهداء
                gift_percentage = int(payment_service.get_setting('gift_percentage', '0'))
                
                # حساب المبلغ الصافي
                net_amount = amount
                if gift_percentage > 0:
                    deduction = int(amount * gift_percentage / 100)
                    net_amount = amount - deduction
                
                # تنفيذ عملية الإهداء
                result = gift_service.send_gift(user_id, receiver_id, amount)
                
                if result['success']:
                    # خصم المبلغ من المرسل
                    balance_result = user_service.subtract_balance(user_id, amount)
                    
                    # إضافة المبلغ للمستلم
                    user_service.add_balance(receiver_id, result['net_amount'])
                    
                    message = (
                        f"✅ **تم إرسال الهدية بنجاح!**\n\n"
                        f"👤 إلى المستخدم: `{receiver_id}`\n"
                        f"💰 المبلغ المُرسل: {amount:,} ليرة\n"
                    )
                    
                    if gift_percentage > 0:
                        message += f"🎯 المبلغ المُستلم: {result['net_amount']:,} ليرة (بعد خصم {gift_percentage}%)\n"
                    
                    message += f"💳 رصيدك الجديد: {balance_result['new']:,} ليرة"
                    
                    bot.edit_message_text(
                        message,
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode="Markdown"
                    )
                    
                    # إرسال إشعار للمستلم
                    try:
                        receiver_msg = (
                            f"🎁 **تلقيت هدية جديدة!**\n\n"
                            f"👤 المرسل: {user_id}\n"
                            f"💰 المبلغ: {amount:,} ليرة\n"
                        )
                        
                        if gift_percentage > 0:
                            receiver_msg += f"🎯 المستلم: {result['net_amount']:,} ليرة (بعد خصم {gift_percentage}%)\n"
                        
                        receiver_balance = user_service.get_user_balance(receiver_id)
                        receiver_msg += f"💳 رصيدك الجديد: {receiver_balance:,} ليرة\n\n"
                        receiver_msg += f"شكراً لك! 🎉"
                        
                        bot.send_message(receiver_id, receiver_msg)
                    except:
                        pass
                else:
                    bot.edit_message_text(
                        f"❌ {result['message']}",
                        call.message.chat.id,
                        call.message.message_id
                    )
                
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"❌ خطأ في تأكيد الإهداء: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_withdraw_"))
    def confirm_withdraw(call):
        """تأكيد عملية السحب"""
        user_id = call.from_user.id
        
        try:
            amount = int(call.data.replace("confirm_withdraw_", ""))
            
            # جلب نسبة السحب
            withdraw_percentage = int(payment_service.get_setting('withdraw_percentage', '0'))
            
            # حساب المبلغ الصافي
            net_amount = amount
            if withdraw_percentage > 0:
                deduction = int(amount * withdraw_percentage / 100)
                net_amount = amount - deduction
            
            bot.edit_message_text(
                "💸 **أدخل تفاصيل السحب**\n\n"
                "📝 أدخل رقم الحساب أو التفاصيل المطلوبة:",
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id)
            
            # Note: Need session service to store withdraw data
            
        except Exception as e:
            logger.error(f"❌ خطأ في تأكيد السحب: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    @bot.callback_query_handler(func=lambda call: call.data in ["cancel_action", "cancel_withdraw", "cancel_gift"])
    def cancel_action(call):
        """إلغاء العملية"""
        try:
            bot.edit_message_text(
                "❌ **تم إلغاء العملية**",
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id, "❌ تم الإلغاء")
        except Exception as e:
            logger.error(f"❌ خطأ في إلغاء العملية: {e}")
    
    @bot.callback_query_handler(func=lambda call: True)
    def handle_other_callbacks(call):
        """معالجة باقي الكال باكات"""
        try:
            # يمكن إضافة معالجات أخرى هنا
            bot.answer_callback_query(call.id, "⚙️ هذه الميزة قيد التطوير")
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الكال باك: {e}")
    
    logger.info("✅ تم تسجيل معالجات الكال باك")