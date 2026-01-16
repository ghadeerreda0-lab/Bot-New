"""
تعريف نماذج الجداول في قاعدة البيانات
"""

class User:
    """نموذج المستخدم"""
    
    def __init__(self, user_id, balance=0, created_at=None, last_active=None,
                 referral_code=None, referred_by=None, is_banned=False,
                 ban_reason=None, ban_until=None):
        self.user_id = user_id
        self.balance = balance
        self.created_at = created_at
        self.last_active = last_active
        self.referral_code = referral_code
        self.referred_by = referred_by
        self.is_banned = is_banned
        self.ban_reason = ban_reason
        self.ban_until = ban_until
    
    def to_dict(self):
        """تحويل النموذج إلى قاموس"""
        return {
            'user_id': self.user_id,
            'balance': self.balance,
            'created_at': self.created_at,
            'last_active': self.last_active,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'is_banned': self.is_banned,
            'ban_reason': self.ban_reason,
            'ban_until': self.ban_until
        }

class Transaction:
    """نموذج المعاملة"""
    
    def __init__(self, transaction_id, user_id, type_, amount, payment_method=None,
                 transaction_id_ext=None, account_number=None, status='pending',
                 created_at=None, notes=None):
        self.id = transaction_id
        self.user_id = user_id
        self.type = type_
        self.amount = amount
        self.payment_method = payment_method
        self.transaction_id = transaction_id_ext
        self.account_number = account_number
        self.status = status
        self.created_at = created_at
        self.notes = notes
    
    def to_dict(self):
        """تحويل النموذج إلى قاموس"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'account_number': self.account_number,
            'status': self.status,
            'created_at': self.created_at,
            'notes': self.notes
        }

class IchancyAccount:
    """نموذج حساب Ichancy"""
    
    def __init__(self, user_id, username, password, balance=0, created_at=None,
                 last_login=None):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.balance = balance
        self.created_at = created_at
        self.last_login = last_login
    
    def to_dict(self):
        """تحويل النموذج إلى قاموس"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'password': self.password,
            'balance': self.balance,
            'created_at': self.created_at,
            'last_login': self.last_login
        }

class Referral:
    """نموذج الإحالة"""
    
    def __init__(self, referral_id, referrer_id, referred_id, amount_charged=0,
                 commission_earned=0, is_active=False, created_at=None):
        self.id = referral_id
        self.referrer_id = referrer_id
        self.referred_id = referred_id
        self.amount_charged = amount_charged
        self.commission_earned = commission_earned
        self.is_active = is_active
        self.created_at = created_at
    
    def to_dict(self):
        """تحويل النموذج إلى قاموس"""
        return {
            'id': self.id,
            'referrer_id': self.referrer_id,
            'referred_id': self.referred_id,
            'amount_charged': self.amount_charged,
            'commission_earned': self.commission_earned,
            'is_active': self.is_active,
            'created_at': self.created_at
        }

class GiftCode:
    """نموذج كود الهدية"""
    
    def __init__(self, code, amount, max_uses=1, used_count=0, created_by=None,
                 created_at=None, expires_at=None):
        self.code = code
        self.amount = amount
        self.max_uses = max_uses
        self.used_count = used_count
        self.created_by = created_by
        self.created_at = created_at
        self.expires_at = expires_at
    
    def to_dict(self):
        """تحويل النموذج إلى قاموس"""
        return {
            'code': self.code,
            'amount': self.amount,
            'max_uses': self.max_uses,
            'used_count': self.used_count,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'expires_at': self.expires_at
        }