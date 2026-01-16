"""
خدمة إدارة نظام Ichancy
"""

import logging
import random
import string
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class IchancyService:
    """خدمة إدارة نظام Ichancy الكامل"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_ichancy_account(self, user_id: int) -> Dict[str, Any]:
        """إنشاء حساب Ichancy جديد"""
        try:
            # التحقق إذا كان لديه حساب بالفعل
            query_check = "SELECT 1 FROM ichancy_accounts WHERE user_id = ?"
            if self.db.execute_query(query_check, (user_id,), fetch_one=True):
                return {"success": False, "message": "❌ لديك حساب Ichancy بالفعل"}
            
            # توليد اسم مستخدم فريد
            username = self._generate_ichancy_username()
            
            # توليد كلمة مرور قوية
            password = self._generate_strong_password()
            
            # إنشاء الحساب
            query_create = """
                INSERT INTO ichancy_accounts (user_id, ichancy_username, ichancy_password, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """
            self.db.execute_query(query_create, (user_id, username, password))
            
            logger.info(f"✅ تم إنشاء حساب Ichancy للمستخدم {user_id}")
            
            return {
                "success": True, 
                "message": "✅ تم إنشاء حساب Ichancy بنجاح!",
                "username": username,
                "password": password,
                "balance": 0
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء حساب Ichancy: {e}")
            return {"success": False, "message": f"❌ خطأ في إنشاء الحساب: {str(e)[:100]}"}
    
    def _generate_ichancy_username(self) -> str:
        """توليد اسم مستخدم فريد لـ Ichancy"""
        adjectives = ["Swift", "Smart", "Fast", "Pro", "Elite", "Gold", "Prime", "Max", "Ultra", "Mega"]
        nouns = ["Player", "Trader", "Master", "Champion", "Warrior", "King", "Legend", "Hero", "Star", "Ace"]
        
        while True:
            adjective = random.choice(adjectives)
            noun = random.choice(nouns)
            number = random.randint(100, 9999)
            username = f"{adjective}{noun}{number}"
            
            # التحقق من التكرار
            query = "SELECT 1 FROM ichancy_accounts WHERE ichancy_username = ?"
            if not self.db.execute_query(query, (username,), fetch_one=True):
                return username
    
    def _generate_strong_password(self, length: int = 10) -> str:
        """توليد كلمة مرور قوية"""
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        symbols = "!@#$%^&*"
        
        # التأكد من وجود حرف كبير، صغير، رقم، ورمز
        password = [
            random.choice(uppercase),
            random.choice(lowercase),
            random.choice(digits),
            random.choice(symbols)
        ]
        
        # إكمال الباقي عشوائياً
        all_chars = uppercase + lowercase + digits + symbols
        password += [random.choice(all_chars) for _ in range(length - 4)]
        
        # خلط الأحرف
        random.shuffle(password)
        return ''.join(password)
    
    def get_ichancy_account(self, user_id: int) -> Optional[Dict[str, Any]]:
        """جلب معلومات حساب Ichancy"""
        try:
            query = """
                SELECT ichancy_username, ichancy_password, ichancy_balance, created_at, last_login
                FROM ichancy_accounts WHERE user_id = ?
            """
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                return {
                    "username": result[0],
                    "password": result[1],
                    "balance": result[2],
                    "created_at": result[3],
                    "last_login": result[4]
                }
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب حساب Ichancy: {e}")
            return None
    
    def update_ichancy_balance(self, user_id: int, amount: int, operation: str = 'add') -> Dict[str, Any]:
        """تحديث رصيد Ichancy"""
        try:
            if operation == 'add':
                query = """
                    UPDATE ichancy_accounts 
                    SET ichancy_balance = ichancy_balance + ?, last_login = datetime('now')
                    WHERE user_id = ?
                """
            elif operation == 'subtract':
                query = """
                    UPDATE ichancy_accounts 
                    SET ichancy_balance = MAX(0, ichancy_balance - ?), last_login = datetime('now')
                    WHERE user_id = ?
                """
            else:
                return {"success": False, "message": "❌ عملية غير صحيحة"}
            
            self.db.execute_query(query, (amount, user_id))
            
            # جلب الرصيد الجديد
            query_balance = "SELECT ichancy_balance FROM ichancy_accounts WHERE user_id = ?"
            result = self.db.execute_query(query_balance, (user_id,), fetch_one=True)
            new_balance = result[0] if result else 0
            
            logger.info(f"✅ تم تحديث رصيد Ichancy للمستخدم {user_id}: {operation} {amount}")
            
            return {"success": True, "new_balance": new_balance}
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث رصيد Ichancy: {e}")
            return {"success": False, "message": str(e)}
    
    def get_ichancy_settings(self) -> Dict[str, bool]:
        """جلب إعدادات Ichancy"""
        try:
            settings = {}
            keys = [
                'ichancy_enabled',
                'ichancy_create_account_enabled',
                'ichancy_deposit_enabled',
                'ichancy_withdraw_enabled'
            ]
            
            for key in keys:
                query = "SELECT value FROM system_settings WHERE key = ?"
                result = self.db.execute_query(query, (key,), fetch_one=True)
                settings[key] = result[0] == 'true' if result else False
            
            return settings
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات Ichancy: {e}")
            return {
                'ichancy_enabled': False,
                'ichancy_create_account_enabled': False,
                'ichancy_deposit_enabled': False,
                'ichancy_withdraw_enabled': False
            }
    
    def update_ichancy_setting(self, key: str, value: bool, admin_id: int = 8146077656) -> bool:
        """تحديث إعداد Ichancy"""
        try:
            str_value = 'true' if value else 'false'
            
            query = """
                INSERT OR REPLACE INTO system_settings (key, value, updated_at, updated_by)
                VALUES (?, ?, datetime('now'), ?)
            """
            self.db.execute_query(query, (key, str_value, admin_id))
            
            logger.info(f"✅ تم تحديث إعداد Ichancy: {key} = {str_value}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعداد Ichancy: {e}")
            return False
    
    def get_all_ichancy_accounts(self, limit: int = 100, offset: int = 0) -> List[tuple]:
        """جلب جميع حسابات Ichancy"""
        try:
            query = """
                SELECT i.user_id, i.ichancy_username, i.ichancy_balance, i.created_at, i.last_login,
                       u.balance as main_balance
                FROM ichancy_accounts i
                JOIN users u ON i.user_id = u.user_id
                ORDER BY i.created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.db.execute_query(query, (limit, offset), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب حسابات Ichancy: {e}")
            return []