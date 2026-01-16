"""
دوال التحقق والتحقق من الصحة
"""

import re
from typing import Union, Optional

def validate_amount(amount: Union[str, int, float], min_amount: int = 1, max_amount: int = 1000000) -> tuple:
    """التحقق من صحة المبلغ"""
    try:
        if isinstance(amount, str):
            # إزالة الفواصل والعملات
            amount = amount.replace(',', '').replace('$', '').replace('ليرة', '').strip()
            
            # التحقق إذا كان رقم
            if not amount.replace('.', '', 1).isdigit():
                return False, "❌ المبلغ غير صحيح، أدخل رقم صحيح فقط"
        
        amount_num = float(amount)
        
        if amount_num <= 0:
            return False, "❌ المبلغ يجب أن يكون أكبر من صفر"
        
        if amount_num < min_amount:
            return False, f"❌ الحد الأدنى للمبلغ هو {min_amount:,}"
        
        if amount_num > max_amount:
            return False, f"❌ الحد الأقصى للمبلغ هو {max_amount:,}"
        
        return True, int(amount_num) if amount_num.is_integer() else amount_num
    
    except Exception as e:
        return False, f"❌ خطأ في التحقق: {str(e)}"

def validate_user_id(user_id: str) -> tuple:
    """التحقق من صحة معرف المستخدم"""
    try:
        if not user_id.isdigit():
            return False, "❌ معرف المستخدم غير صحيح، أدخل أرقام فقط"
        
        user_id_num = int(user_id)
        
        if user_id_num <= 0:
            return False, "❌ معرف المستخدم غير صحيح"
        
        return True, user_id_num
    
    except Exception as e:
        return False, f"❌ خطأ في التحقق: {str(e)}"

def validate_gift_code(code: str) -> bool:
    """التحقق من صحة كود الهدية"""
    if not code or len(code) < 5 or len(code) > 10:
        return False
    
    # يجب أن يحتوي على أحرف وأرقام فقط
    if not re.match(r'^[A-Z0-9]+$', code.upper()):
        return False
    
    return True

def validate_percentage(percentage: str) -> tuple:
    """التحقق من صحة النسبة"""
    try:
        if not percentage.isdigit():
            return False, "❌ النسبة غير صحيحة، أدخل أرقام فقط"
        
        percentage_num = int(percentage)
        
        if percentage_num < 0 or percentage_num > 100:
            return False, "❌ النسبة يجب أن تكون بين 0 و 100"
        
        return True, percentage_num
    
    except Exception as e:
        return False, f"❌ خطأ في التحقق: {str(e)}"

def validate_phone_number(phone: str) -> bool:
    """التحقق من صحة رقم الهاتف"""
    # أبسط تحقق لرقم سوري
    if not phone:
        return False
    
    # إزالة المسافات والشارة +
    phone = phone.replace(' ', '').replace('+', '')
    
    # يجب أن يبدأ بـ 09 أو 9 ويحتوي على 9-10 أرقام
    if re.match(r'^(09|\+?9639|9)\d{8}$', phone):
        return True
    
    return False

def validate_transaction_id(tx_id: str) -> bool:
    """التحقق من صحة رقم المعاملة"""
    if not tx_id or len(tx_id) < 5:
        return False
    
    # يمكن أن يحتوي على أحرف وأرقام
    return True