"""
مكتبة الأمان والتشفير
"""
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from cryptography.fernet import Fernet
import base64
from config import Config
import logging

logger = logging.getLogger(__name__)

class SecurityUtils:
    @staticmethod
    def generate_referral_code(length: int = 8) -> str:
        """إنشاء كود إحالة فريد"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_gift_code(length: int = 10) -> str:
        """إنشاء كود هدية فريد"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """إنشاء كلمة سر قوية"""
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        symbols = "!@#$%^&*"
        
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]
        
        all_chars = uppercase + lowercase + digits + symbols
        password += [secrets.choice(all_chars) for _ in range(length - 4)]
        
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """تجزئة كلمة المرور"""
        salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return base64.b64encode(salt + key).decode('utf-8')
    
    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """التحقق من كلمة المرور"""
        try:
            decoded = base64.b64decode(stored_hash)
            salt = decoded[:16]
            stored_key = decoded[16:]
            
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000
            )
            return hmac.compare_digest(key, stored_key)
        except:
            return False
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """تشفير البيانات الحساسة"""
        fernet = Fernet(base64.b64encode(Config.ENCRYPTION_KEY.encode()[:32].ljust(32)))
        encrypted = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """فك تشفير البيانات"""
        try:
            fernet = Fernet(base64.b64encode(Config.ENCRYPTION_KEY.encode()[:32].ljust(32)))
            decrypted = fernet.decrypt(base64.b64decode(encrypted_data))
            return decrypted.decode()
        except:
            return ""
    
    @staticmethod
    def generate_jwt_token(user_id: int, user_type: str = "user") -> str:
        """إنشاء JWT token"""
        payload = {
            'user_id': user_id,
            'user_type': user_type,
            'exp': datetime.utcnow() + timedelta(days=7),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[Dict]:
        """التحقق من JWT token"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token منتهي الصلاحية")
            return None
        except jwt.InvalidTokenError:
            logger.warning("JWT token غير صالح")
            return None
    
    @staticmethod
    def generate_transaction_code() -> str:
        """إنشاء رقم عملية فريد"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(3).upper()
        return f"TX{timestamp}{random_part}"
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """التحقق من صحة رقم الهاتف السوري"""
        # أرقام سورية: 09xxxxxxxx أو +9639xxxxxxxx
        phone = phone.replace("+", "").replace(" ", "")
        
        if phone.startswith("963"):
            phone = phone[3:]  # إزالة مفتاح الدولة
        elif phone.startswith("0"):
            phone = phone[1:]  # إزالة الصفر
        
        if len(phone) != 9:
            return False
        
        if not phone.startswith("9"):
            return False
        
        return phone.isdigit()
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """تنظيف إدخال المستخدم"""
        import html
        # إزالة علامات HTML
        text = html.escape(text)
        # إزالة المسافات الزائدة
        text = ' '.join(text.split())
        # تحديد الطول الأقصى
        if len(text) > max_length:
            text = text[:max_length]
        return text
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """إنشاء OTP"""
        digits = string.digits
        return ''.join(secrets.choice(digits) for _ in range(length))
    
    @staticmethod
    def check_rate_limit(key: str, limit: int = 10, window: int = 60) -> bool:
        """التحقق من حد المعدل"""
        import time
        from redis import Redis
        from config import Config
        
        try:
            redis_client = Redis.from_url(Config.REDIS_URL)
            current = int(time.time())
            window_start = current - window
            
            # إزالة الطلبات القديمة
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # عد الطلبات الحالية
            request_count = redis_client.zcard(key)
            
            if request_count >= limit:
                return False
            
            # إضافة الطلب الجديد
            redis_client.zadd(key, {str(current): current})
            redis_client.expire(key, window + 10)
            return True
        except:
            return True  # في حالة فشل Redis، نسمح بالطلب
    
    @staticmethod
    def create_hmac_signature(data: str, secret: str) -> str:
        """إنشاء توقيع HMAC"""
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
        """التحقق من توقيع HMAC"""
        expected_signature = SecurityUtils.create_hmac_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)

# دوال مساعدة سريعة
def generate_referral_code():
    return SecurityUtils.generate_referral_code()

def generate_gift_code():
    return SecurityUtils.generate_gift_code()

def encrypt_data(data):
    return SecurityUtils.encrypt_data(data)

def decrypt_data(data):
    return SecurityUtils.decrypt_data(data)