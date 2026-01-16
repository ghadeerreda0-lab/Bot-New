"""
دوال توليد الأكواد والأرقام العشوائية
"""

import random
import string
from datetime import datetime
from typing import Optional

def generate_referral_code(user_id: int) -> str:
    """توليد كود إحالة فريد"""
    # استخدام آخر 6 أرقام من user_id مع أحرف عشوائية
    base = str(user_id)[-6:] if len(str(user_id)) >= 6 else str(user_id).zfill(6)
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=2))
    code = f"REF{base}{random_part}"
    
    return code

def generate_order_number(month: int, year: int, counter: int, payment_method: str) -> str:
    """توليد رقم طلب شهري"""
    method_codes = {
        'syriatel_cash': 'SYC',
        'sham_cash': 'SHC',
        'sham_cash_usd': 'SHD'
    }
    
    method_code = method_codes.get(payment_method, 'GEN')
    return f"{method_code}{year%100:02d}{month:02d}{counter:04d}"

def generate_random_code(length: int = 7, prefix: str = "") -> str:
    """توليد كود عشوائي"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=length))
    return f"{prefix}{code}"

def generate_username_suggestion(base_name: str) -> str:
    """توليد اقتراح لاسم مستخدم"""
    suggestions = []
    
    # إضافة أرقام
    for i in range(3):
        suggestions.append(f"{base_name}{random.randint(100, 999)}")
    
    # إضافة سنة
    current_year = datetime.now().year % 100
    suggestions.append(f"{base_name}{current_year}")
    
    # إضافة أحرف عشوائية
    chars = string.ascii_lowercase
    suggestions.append(f"{base_name}{random.choice(chars)}{random.randint(10, 99)}")
    
    return random.choice(suggestions)

def generate_password(length: int = 12) -> str:
    """توليد كلمة مرور قوية"""
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*"
    
    # التأكد من وجود أنواع مختلفة من الأحرف
    password_chars = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(symbols)
    ]
    
    # إكمال الباقي
    all_chars = uppercase + lowercase + digits + symbols
    password_chars += [random.choice(all_chars) for _ in range(length - 4)]
    
    # خلط الأحرف
    random.shuffle(password_chars)
    return ''.join(password_chars)

def generate_display_amount(amount: int) -> str:
    """توليد نص معروض للمبلغ"""
    if amount >= 1000000:
        return f"{amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K"
    else:
        return f"{amount:,}"