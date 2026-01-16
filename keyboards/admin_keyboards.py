"""
لوحات مفاتيح الأدمن
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.payment_service import PaymentService

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """لوحة تحكم الأدمن"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("⚙️ الإعدادات العامة", callback_data="admin_general_settings"),
        InlineKeyboardButton("💰 إعدادات الدفع", callback_data="admin_payment_settings")
    )
    
    kb.row(
        InlineKeyboardButton("💸 إعدادات السحب", callback_data="admin_withdraw_settings"),
        InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users_management")
    )
    
    kb.row(
        InlineKeyboardButton("📊 التقارير والإحصائيات", callback_data="admin_reports"),
        InlineKeyboardButton("🤝 إعدادات الاحالات", callback_data="admin_referral_settings")
    )
    
    kb.row(
        InlineKeyboardButton("⚡ نظام Ichancy", callback_data="admin_ichancy_settings"),
        InlineKeyboardButton("📋 المعاملات", callback_data="admin_transactions")
    )
    
    kb.add(InlineKeyboardButton("👑 إدارة الأدمن", callback_data="admin_manage_admins"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع للقائمة", callback_data="back"))
    
    return kb

def general_settings_keyboard(payment_service: PaymentService) -> InlineKeyboardMarkup:
    """إعدادات عامة"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    # حالة Ichancy
    ichancy_enabled = payment_service.get_setting('ichancy_enabled') == 'true'
    ichancy_create = payment_service.get_setting('ichancy_create_account_enabled') == 'true'
    ichancy_deposit = payment_service.get_setting('ichancy_deposit_enabled') == 'true'
    ichancy_withdraw = payment_service.get_setting('ichancy_withdraw_enabled') == 'true'
    
    # حالة الشحن والسحب
    deposit_enabled = payment_service.get_setting('deposit_enabled') == 'true'
    withdraw_enabled = payment_service.get_setting('withdraw_enabled') == 'true'
    withdraw_btn_visible = payment_service.get_setting('withdraw_button_visible') == 'true'
    maintenance_mode = payment_service.get_setting('maintenance_mode') == 'true'
    
    # قسم Ichancy
    kb.add(InlineKeyboardButton(
        f"⚡ Ichancy: {'✅' if ichancy_enabled else '❌'}", 
        callback_data="admin_toggle_ichancy"
    ))
    
    kb.row(
        InlineKeyboardButton(
            f"📝 إنشاء حساب: {'✅' if ichancy_create else '❌'}", 
            callback_data="admin_toggle_ichancy_create"
        ),
        InlineKeyboardButton(
            f"💰 الشحن: {'✅' if ichancy_deposit else '❌'}", 
            callback_data="admin_toggle_ichancy_deposit"
        )
    )
    
    kb.add(InlineKeyboardButton(
        f"💸 السحب: {'✅' if ichancy_withdraw else '❌'}", 
        callback_data="admin_toggle_ichancy_withdraw"
    ))
    
    # قسم الشحن والسحب
    kb.add(InlineKeyboardButton(
        f"💰 الشحن العام: {'✅' if deposit_enabled else '❌'}", 
        callback_data="admin_toggle_deposit"
    ))
    
    kb.row(
        InlineKeyboardButton(
            f"💸 السحب العام: {'✅' if withdraw_enabled else '❌'}", 
            callback_data="admin_toggle_withdraw"
        ),
        InlineKeyboardButton(
            f"👁️ زر السحب: {'👁️' if withdraw_btn_visible else '👁️‍🗨️'}", 
            callback_data="admin_toggle_withdraw_button"
        )
    )
    
    kb.add(InlineKeyboardButton(
        f"🛠️ الصيانة: {'✅' if maintenance_mode else '❌'}", 
        callback_data="admin_toggle_maintenance"
    ))
    
    # الرسائل
    kb.row(
        InlineKeyboardButton("✏️ رسالة الترحيب", callback_data="admin_edit_welcome_msg"),
        InlineKeyboardButton("✏️ رسالة الصيانة", callback_data="admin_edit_maintenance_msg")
    )
    
    kb.row(
        InlineKeyboardButton("📊 التقارير اليومية", callback_data="admin_daily_report"),
        InlineKeyboardButton("📁 نسخ احتياطي", callback_data="admin_backup_now")
    )
    
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def payment_settings_keyboard(payment_service: PaymentService) -> InlineKeyboardMarkup:
    """إعدادات الدفع"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    methods = payment_service.get_payment_methods()
    
    for method_id, method_info in methods.items():
        enabled = method_info['enabled']
        visible = method_info['visible']
        
        status = ""
        if enabled and visible:
            status = "✅👁️"
        elif enabled and not visible:
            status = "✅👁️‍🗨️"
        elif not enabled and visible:
            status = "⏸️👁️"
        else:
            status = "❌👁️‍🗨️"
        
        if method_id == 'syriatel_cash':
            kb.add(InlineKeyboardButton(
                f"📱 سيرياتيل كاش {status}", 
                callback_data="admin_syriatel_settings"
            ))
        elif method_id == 'sham_cash':
            kb.add(InlineKeyboardButton(
                f"💰 شام كاش {status}", 
                callback_data="admin_sham_settings"
            ))
        elif method_id == 'sham_cash_usd':
            kb.add(InlineKeyboardButton(
                f"💵 شام كاش دولار {status}", 
                callback_data="admin_sham_usd_settings"
            ))
    
    kb.add(InlineKeyboardButton("💰 حدود المبالغ", callback_data="admin_payment_limits"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def withdraw_settings_keyboard(payment_service: PaymentService) -> InlineKeyboardMarkup:
    """إعدادات السحب"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    withdraw_enabled = payment_service.get_setting('withdraw_enabled') == 'true'
    withdraw_btn_visible = payment_service.get_setting('withdraw_button_visible') == 'true'
    withdraw_percentage = payment_service.get_setting('withdraw_percentage', '0')
    
    kb.row(
        InlineKeyboardButton(
            f"⚡ تفعيل/إيقاف: {'✅' if withdraw_enabled else '❌'}", 
            callback_data="admin_toggle_withdraw"
        ),
        InlineKeyboardButton(
            f"👁️ زر السحب: {'👁️' if withdraw_btn_visible else '👁️‍🗨️'}", 
            callback_data="admin_toggle_withdraw_button"
        )
    )
    
    kb.row(
        InlineKeyboardButton(
            f"📊 نسبة السحب: {withdraw_percentage}%", 
            callback_data="admin_edit_withdraw_percentage"
        ),
        InlineKeyboardButton("💰 حدود السحب", callback_data="admin_withdraw_limits")
    )
    
    kb.row(
        InlineKeyboardButton("📝 رسالة التوقف", callback_data="admin_edit_withdraw_msg"),
        InlineKeyboardButton("📊 إحصائيات السحب", callback_data="admin_withdraw_stats")
    )
    
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def users_management_keyboard() -> InlineKeyboardMarkup:
    """إدارة المستخدمين"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("👥 عدد المستخدمين", callback_data="admin_users_count"),
        InlineKeyboardButton("💰 إضافة رصيد", callback_data="admin_add_balance")
    )
    
    kb.row(
        InlineKeyboardButton("💸 سحب رصيد", callback_data="admin_subtract_balance"),
        InlineKeyboardButton("📊 رصيد المستخدمين", callback_data="admin_users_balance")
    )
    
    kb.row(
        InlineKeyboardButton("📨 رسالة لمستخدم", callback_data="admin_message_user"),
        InlineKeyboardButton("🖼️ صورة لمستخدم", callback_data="admin_photo_user")
    )
    
    kb.row(
        InlineKeyboardButton("📣 رسالة للجميع", callback_data="admin_broadcast"),
        InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user")
    )
    
    kb.row(
        InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="admin_unban_user"),
        InlineKeyboardButton("🗑️ حذف حساب", callback_data="admin_delete_user")
    )
    
    kb.row(
        InlineKeyboardButton("🏆 أعلى رصيد", callback_data="admin_top_balance"),
        InlineKeyboardButton("⭐ اللاعبين المميزين", callback_data="admin_top_deposit")
    )
    
    kb.row(
        InlineKeyboardButton("💸 سحب جميع الأرصدة", callback_data="admin_reset_all_balances"),
        InlineKeyboardButton("📜 جلب سجل لاعب", callback_data="admin_user_logs")
    )
    
    kb.add(InlineKeyboardButton("🎁 تعديل نسبة الإهداء", callback_data="admin_edit_gift_percentage"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def referral_settings_keyboard(referral_service) -> InlineKeyboardMarkup:
    """إعدادات الإحالات"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    settings = referral_service.get_referral_settings()
    
    commission_rate = settings.get('commission_rate', 10)
    bonus_amount = settings.get('bonus_amount', 2000)
    min_active = settings.get('min_active_referrals', 5)
    min_charge = settings.get('min_charge_amount', 100000)
    next_dist = settings.get('next_distribution', 'غير محدد')
    
    kb.row(
        InlineKeyboardButton(
            f"📊 النسبة: {commission_rate}%", 
            callback_data="admin_edit_referral_rate"
        ),
        InlineKeyboardButton(
            f"💰 المكافأة: {bonus_amount:,}", 
            callback_data="admin_edit_referral_bonus"
        )
    )
    
    kb.row(
        InlineKeyboardButton(
            f"👥 الحد الأدنى: {min_active}", 
            callback_data="admin_edit_min_referrals"
        ),
        InlineKeyboardButton(
            f"💸 حد الشحن: {min_charge:,}", 
            callback_data="admin_edit_min_charge"
        )
    )
    
    kb.row(
        InlineKeyboardButton(
            f"⏰ موعد التوزيع: {next_dist}", 
            callback_data="admin_edit_distribution_time"
        ),
        InlineKeyboardButton("📈 أعلى الاحالات", callback_data="admin_top_referrals")
    )
    
    kb.add(InlineKeyboardButton("💸 توزيع النسب", callback_data="admin_distribute_referrals"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def ichancy_settings_keyboard(payment_service: PaymentService) -> InlineKeyboardMarkup:
    """إعدادات Ichancy"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    ichancy_enabled = payment_service.get_setting('ichancy_enabled') == 'true'
    create_enabled = payment_service.get_setting('ichancy_create_account_enabled') == 'true'
    deposit_enabled = payment_service.get_setting('ichancy_deposit_enabled') == 'true'
    withdraw_enabled = payment_service.get_setting('ichancy_withdraw_enabled') == 'true'
    
    kb.row(
        InlineKeyboardButton(
            f"⚡ Ichancy: {'✅' if ichancy_enabled else '❌'}", 
            callback_data="admin_toggle_ichancy"
        ),
        InlineKeyboardButton(
            f"📝 إنشاء حساب: {'✅' if create_enabled else '❌'}", 
            callback_data="admin_toggle_ichancy_create"
        )
    )
    
    kb.row(
        InlineKeyboardButton(
            f"💰 الشحن: {'✅' if deposit_enabled else '❌'}", 
            callback_data="admin_toggle_ichancy_deposit"
        ),
        InlineKeyboardButton(
            f"💸 السحب: {'✅' if withdraw_enabled else '❌'}", 
            callback_data="admin_toggle_ichancy_withdraw"
        )
    )
    
    kb.add(InlineKeyboardButton("✏️ رسالة Ichancy", callback_data="admin_edit_ichancy_msg"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def reports_keyboard() -> InlineKeyboardMarkup:
    """التقارير والإحصائيات"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("📅 تقرير اليوم", callback_data="report_today"),
        InlineKeyboardButton("📆 تقرير الأمس", callback_data="report_yesterday")
    )
    
    kb.row(
        InlineKeyboardButton("💰 تقرير الشحن", callback_data="report_deposit"),
        InlineKeyboardButton("💸 تقرير السحب", callback_data="report_withdraw")
    )
    
    kb.row(
        InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="report_users"),
        InlineKeyboardButton("📈 أداء النظام", callback_data="report_system")
    )
    
    kb.row(
        InlineKeyboardButton("📱 إحصائيات الأكواد", callback_data="report_codes"),
        InlineKeyboardButton("🔄 تحديث البيانات", callback_data="report_refresh")
    )
    
    kb.add(InlineKeyboardButton("📥 تصدير البيانات", callback_data="report_export"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def manage_admins_keyboard() -> InlineKeyboardMarkup:
    """إدارة الأدمن"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin_add_admin"),
        InlineKeyboardButton("🗑️ حذف أدمن", callback_data="admin_remove_admin")
    )
    
    kb.add(InlineKeyboardButton("📋 عرض جميع الأدمن", callback_data="admin_list_admins"))
    kb.add(InlineKeyboardButton("⬅ ↩️ رجوع", callback_data="admin_back_to_panel"))
    
    return kb

def transaction_approval_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """موافقة/رفض معاملة"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("✅ قبول", callback_data=f"approve_{transaction_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{transaction_id}")
    )
    
    return kb

def confirmation_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """لوحة تأكيد للعمليات الخطيرة"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    kb.row(
        InlineKeyboardButton("✅ نعم، تأكيد", callback_data=f"confirm_{action}_{data}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
    )
    
    return kb