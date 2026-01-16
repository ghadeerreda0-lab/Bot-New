"""
لوحات مفاتيح المستخدمين
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.ichancy_service import IchancyService
from services.payment_service import PaymentService

def main_menu_keyboard(user_id: int, ichancy_service: IchancyService) -> InlineKeyboardMarkup:
    """القائمة الرئيسية للمستخدم"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    # زر Ichancy
    ichancy_account = ichancy_service.get_ichancy_account(user_id)
    if ichancy_account:
        kb.add(InlineKeyboardButton("⚡ Ichancy - معلومات الحساب", callback_data="ichancy_info"))
    else:
        kb.add(InlineKeyboardButton("⚡ Ichancy - إنشاء حساب", callback_data="ichancy_info"))
    
    # زر شحن رصيد
    kb.add(InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit_menu"))
    
    # زر سحب رصيد (إذا كان مفعلاً ومرئياً)
    # Note: Need payment_service to check settings
    
    # باقي الأزرار
    kb.row(
        InlineKeyboardButton("🤝 نظام الاحالات", callback_data="referrals"),
        InlineKeyboardButton("🎁 اهداء رصيد", callback_data="gift_balance")
    )
    
    kb.row(
        InlineKeyboardButton("🎁 كود هدية", callback_data="gift_code"),
        InlineKeyboardButton("📜 السجل", callback_data="user_logs")
    )
    
    kb.row(
        InlineKeyboardButton("✉️ تواصل مع الدعم", callback_data="support"),
        InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")
    )
    
    kb.add(InlineKeyboardButton("📌 الشروط والأحكام", callback_data="rules"))
    
    # Note: Admin panel button will be added in admin handlers
    
    return kb

def deposit_menu_keyboard(payment_service: PaymentService) -> InlineKeyboardMarkup:
    """قائمة طرق الشحن"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    methods = payment_service.get_payment_methods()
    visible_methods = []
    
    for method_id, method_info in methods.items():
        if method_info['visible'] and method_info['enabled']:
            visible_methods.append(
                InlineKeyboardButton(method_info['name'], callback_data=f"pay_{method_id}")
            )
    
    # ترتيب الأزرار
    if len(visible_methods) >= 2:
        kb.row(visible_methods[0], visible_methods[1])
        if len(visible_methods) > 2:
            kb.add(visible_methods[2])
    elif visible_methods:
        kb.add(visible_methods[0])
    
    kb.add(InlineKeyboardButton("⬅️ ↩️ رجوع", callback_data="back"))
    return kb

def ichancy_menu_keyboard(has_account: bool) -> InlineKeyboardMarkup:
    """قائمة Ichancy"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    if has_account:
        kb.row(
            InlineKeyboardButton("💰 شحن في Ichancy", callback_data="ichancy_deposit"),
            InlineKeyboardButton("💸 سحب من Ichancy", callback_data="ichancy_withdraw")
        )
    else:
        kb.add(InlineKeyboardButton("⚡ إنشاء حساب Ichancy", callback_data="ichancy_create"))
    
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="back"))
    return kb

def user_logs_keyboard() -> InlineKeyboardMarkup:
    """سجل المستخدم الشخصي"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("💳 عمليات الشحن", callback_data="user_deposit_logs"),
        InlineKeyboardButton("💸 عمليات السحب", callback_data="user_withdraw_logs")
    )
    
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="back"))
    return kb

def withdraw_confirmation_keyboard(withdraw_percentage: int, amount: int, net_amount: int) -> InlineKeyboardMarkup:
    """تأكيد عملية السحب"""
    kb = InlineKeyboardMarkup()
    
    if withdraw_percentage > 0:
        message = f"📊 نسبة السحب: {withdraw_percentage}%\n💸 المبلغ: {amount:,} → {net_amount:,} ليرة"
    else:
        message = f"💰 المبلغ: {amount:,} ليرة"
    
    kb.row(
        InlineKeyboardButton("✅ تأكيد السحب", callback_data=f"confirm_withdraw_{amount}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_withdraw")
    )
    
    return kb

def gift_confirmation_keyboard(receiver_id: int, amount: int, net_amount: int, gift_percentage: int) -> InlineKeyboardMarkup:
    """تأكيد عملية الإهداء"""
    kb = InlineKeyboardMarkup()
    
    if gift_percentage > 0:
        message = f"🎁 إهداء لـ {receiver_id}\n📊 نسبة: {gift_percentage}%\n💸 المبلغ: {amount:,} → {net_amount:,} ليرة"
    else:
        message = f"🎁 إهداء لـ {receiver_id}\n💰 المبلغ: {amount:,} ليرة"
    
    kb.row(
        InlineKeyboardButton("✅ تأكيد الإهداء", callback_data=f"confirm_gift_{receiver_id}_{amount}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_gift")
    )
    
    return kb