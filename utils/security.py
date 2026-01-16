"""
دوال الأمان والتشفير
"""

import hashlib
import secrets
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """مدير الأمان للتشفير والتحقق"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or "default_secret_key_change_in_production"
    
    def hash_password(self, password: str) -> str:
        """تشفير كلمة المرور"""
        try:
            # استخدام SHA256 مع salt
            salt = secrets.token_hex(16)
            hash_obj = hashlib.sha256()
            hash_obj.update(f"{password}{salt}{self.secret_key}".encode('utf-8'))
            return f"{salt}${hash_obj.hexdigest()}"
        except Exception as e:
            logger.error(f"❌ خطأ في تشفير كلمة المرور: {e}")
            return ""
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """التحقق من كلمة المرور"""
        try:
            if not hashed_password or '$' not in hashed_password:
                return False
            
            salt, stored_hash = hashed_password.split('$', 1)
            hash_obj = hashlib.sha256()
            hash_obj.update(f"{password}{salt}{self.secret_key}".encode('utf-8'))
            return hash_obj.hexdigest() == stored_hash
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من كلمة المرور: {e}")
            return False
    
    def generate_token(self, length: int = 32) -> str:
        """توليد توكن آمن"""
        return secrets.token_urlsafe(length)
    
    def sanitize_input(self, text: str) -> str:
        """تنظيف الإدخال من الأحرف الخطيرة"""
        if not text:
            return ""
        
        # إزالة الأحرف الخطيرة
        dangerous_chars = ['<', '>', '"', "'", ';', '\\', '/', '`']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # تقليل المسافات المتعددة
        text = ' '.join(text.split())
        
        return text.strip()
    
    def validate_input_length(self, text: str, min_length: int = 1, max_length: int = 1000) -> bool:
        """التحقق من طول الإدخال"""
        if not text:
            return False
        
        length = len(text)
        return min_length <= length <= max_length

# إنشاء كائن أمان افتراضي
security = SecurityManager()