"""
خدمة إدارة نظام الهدايا والإهداء
"""

import logging
import random
import string
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class GiftService:
    """خدمة إدارة نظام الهدايا والإهداء"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def generate_gift_code(self, amount: int, max_uses: int = 1, expires_days: int = 30, 
                          created_by: int = None) -> Dict[str, Any]:
        """توليد كود هدية فريد"""
        try:
            # توليد كود فريد
            code = self._generate_unique_code()
            
            # حساب تاريخ الانتهاء
            expires_at = None
            if expires_days > 0:
                expires_at = (datetime.now() + timedelta(days=expires_days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # إضافة الكود إلى قاعدة البيانات
            query = """
                INSERT INTO gift_codes (code, amount, max_uses, created_by, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """
            self.db.execute_query(query, (code, amount, max_uses, created_by, expires_at))
            
            logger.info(f"✅ تم إنشاء كود هدية: {code} بقيمة {amount} ليرة")
            return {"success": True, "code": code, "amount": amount}
            
        except Exception as e:
            logger.error(f"❌ خطأ في توليد كود هدية: {e}")
            return {"success": False, "message": str(e)}
    
    def _generate_unique_code(self, length: int = 7) -> str:
        """توليد كود فريد"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            
            # التحقق من التكرار
            query = "SELECT 1 FROM gift_codes WHERE code = ?"
            result = self.db.execute_query(query, (code,), fetch_one=True)
            
            if not result:
                return code
    
    def use_gift_code(self, code: str, user_id: int) -> Dict[str, Any]:
        """استخدام كود هدية"""
        try:
            # التحقق من صلاحية الكود
            query_check = """
                SELECT amount, max_uses, used_count, expires_at 
                FROM gift_codes WHERE code = ?
            """
            result = self.db.execute_query(query_check, (code,), fetch_one=True)
            
            if not result:
                return {"success": False, "message": "❌ كود الهدية غير صحيح"}
            
            amount, max_uses, used_count, expires_at = result
            
            # التحقق من عدد الاستخدامات
            if used_count >= max_uses:
                return {"success": False, "message": "❌ هذا الكود مستخدم بالفعل"}
            
            # التحقق من الصلاحية الزمنية
            if expires_at and datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S') < datetime.now():
                return {"success": False, "message": "❌ انتهت صلاحية هذا الكود"}
            
            # التحقق إذا استخدمه المستخدم سابقاً
            query_usage = "SELECT 1 FROM gift_code_usage WHERE code = ? AND user_id = ?"
            if self.db.execute_query(query_usage, (code, user_id), fetch_one=True):
                return {"success": False, "message": "❌ لقد استخدمت هذا الكود مسبقاً"}
            
            # زيادة عداد الاستخدام
            query_update = "UPDATE gift_codes SET used_count = used_count + 1 WHERE code = ?"
            self.db.execute_query(query_update, (code,))
            
            # تسجيل الاستخدام
            query_usage_log = """
                INSERT INTO gift_code_usage (code, user_id, used_at)
                VALUES (?, ?, datetime('now'))
            """
            self.db.execute_query(query_usage_log, (code, user_id))
            
            logger.info(f"✅ تم استخدام كود هدية {code} من قبل المستخدم {user_id}")
            return {"success": True, "amount": amount, "code": code}
            
        except Exception as e:
            logger.error(f"❌ خطأ في استخدام كود هدية: {e}")
            return {"success": False, "message": f"❌ خطأ في تفعيل الكود: {str(e)[:100]}"}
    
    def send_gift(self, sender_id: int, receiver_id: int, amount: int) -> Dict[str, Any]:
        """إرسال هدية من مستخدم لآخر"""
        try:
            # التحقق من وجود المستلم
            query_receiver = "SELECT 1 FROM users WHERE user_id = ?"
            if not self.db.execute_query(query_receiver, (receiver_id,), fetch_one=True):
                return {"success": False, "message": "❌ المستخدم غير موجود"}
            
            # التحقق من عدم إهداء النفس
            if sender_id == receiver_id:
                return {"success": False, "message": "❌ لا يمكن إهداء نفسك"}
            
            # جلب نسبة الإهداء
            query_setting = "SELECT value FROM system_settings WHERE key = 'gift_percentage'"
            result = self.db.execute_query(query_setting, fetch_one=True)
            gift_percentage = int(result[0]) if result else 0
            
            # حساب المبلغ الصافي
            net_amount = amount
            if gift_percentage > 0:
                deduction = int(amount * gift_percentage / 100)
                net_amount = amount - deduction
            
            # تسجيل عملية الإهداء
            query_gift = """
                INSERT INTO gift_transactions (sender_id, receiver_id, original_amount, 
                                              net_amount, gift_percentage, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """
            gift_id = self.db.execute_query(query_gift, (sender_id, receiver_id, amount, net_amount, gift_percentage))
            
            logger.info(f"✅ تم إرسال هدية #{gift_id} من {sender_id} إلى {receiver_id}")
            
            return {
                "success": True,
                "gift_id": gift_id,
                "original_amount": amount,
                "net_amount": net_amount,
                "gift_percentage": gift_percentage,
                "deduction": amount - net_amount if gift_percentage > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال هدية: {e}")
            return {"success": False, "message": f"❌ خطأ في إرسال الهدية: {str(e)[:100]}"}
    
    def get_gift_codes(self, limit: int = 50, offset: int = 0) -> List[tuple]:
        """جلب أكواد الهدايا"""
        try:
            query = """
                SELECT code, amount, max_uses, used_count, created_by, created_at, expires_at
                FROM gift_codes 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.db.execute_query(query, (limit, offset), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أكواد الهدايا: {e}")
            return []
    
    def get_gift_transactions(self, user_id: int = None, limit: int = 50, offset: int = 0) -> List[tuple]:
        """جلب عمليات الإهداء"""
        try:
            query_base = """
                SELECT id, sender_id, receiver_id, original_amount, net_amount, gift_percentage, created_at
                FROM gift_transactions 
            """
            params = []
            
            if user_id:
                query_base += " WHERE sender_id = ? OR receiver_id = ?"
                params.extend([user_id, user_id])
            
            query_base += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            return self.db.execute_query(query_base, tuple(params), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عمليات الإهداء: {e}")
            return []