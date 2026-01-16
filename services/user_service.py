"""
خدمة إدارة المستخدمين
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class UserService:
    """خدمة إدارة جميع عمليات المستخدمين"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._cache = {}  # كاش بسيط للأدمن
    
    def create_user(self, user_id: int) -> bool:
        """إنشاء مستخدم جديد"""
        try:
            # التحقق من وجود المستخدم
            existing = self.get_user(user_id)
            if existing:
                return True
            
            # توليد كود إحالة
            from utils.generators import generate_referral_code
            referral_code = generate_referral_code(user_id)
            
            query = """
                INSERT INTO users (user_id, balance, created_at, last_active, referral_code) 
                VALUES (?, 0, datetime('now'), datetime('now'), ?)
            """
            self.db.execute_query(query, (user_id, referral_code))
            
            logger.info(f"✅ تم إنشاء مستخدم جديد: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء مستخدم: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """جلب بيانات مستخدم"""
        try:
            query = """
                SELECT user_id, balance, created_at, last_active, referral_code, 
                       is_banned, ban_reason, ban_until 
                FROM users WHERE user_id = ?
            """
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                # تحديث آخر نشاط
                update_query = "UPDATE users SET last_active = datetime('now') WHERE user_id = ?"
                self.db.execute_query(update_query, (user_id,))
                
                return {
                    'user_id': result[0],
                    'balance': result[1],
                    'created_at': result[2],
                    'last_active': result[3],
                    'referral_code': result[4],
                    'is_banned': bool(result[5]),
                    'ban_reason': result[6],
                    'ban_until': result[7]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
    
    def get_user_balance(self, user_id: int) -> int:
        """جلب رصيد المستخدم"""
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def add_balance(self, user_id: int, amount: int) -> Dict[str, int]:
        """إضافة رصيد للمستخدم"""
        try:
            old_balance = self.get_user_balance(user_id)
            new_balance = old_balance + amount
            
            query = "UPDATE users SET balance = ? WHERE user_id = ?"
            self.db.execute_query(query, (new_balance, user_id))
            
            logger.info(f"✅ تم إضافة {amount} ليرة للمستخدم {user_id}")
            return {'old': old_balance, 'new': new_balance}
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة رصيد: {e}")
            return {'old': 0, 'new': 0}
    
    def subtract_balance(self, user_id: int, amount: int) -> Dict[str, int]:
        """خصم رصيد من المستخدم"""
        try:
            old_balance = self.get_user_balance(user_id)
            new_balance = max(0, old_balance - amount)
            
            query = "UPDATE users SET balance = ? WHERE user_id = ?"
            self.db.execute_query(query, (new_balance, user_id))
            
            logger.info(f"✅ تم خصم {amount} ليرة من المستخدم {user_id}")
            return {'old': old_balance, 'new': new_balance}
            
        except Exception as e:
            logger.error(f"❌ خطأ في خصم رصيد: {e}")
            return {'old': 0, 'new': 0}
    
    def get_all_users(self, limit: int = 1000, offset: int = 0) -> List[tuple]:
        """جلب جميع المستخدمين"""
        try:
            query = """
                SELECT user_id, balance, created_at, last_active, is_banned
                FROM users 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.db.execute_query(query, (limit, offset), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع المستخدمين: {e}")
            return []
    
    def get_users_count(self) -> Dict[str, int]:
        """جلب إحصائيات المستخدمين"""
        try:
            query_total = "SELECT COUNT(*) FROM users"
            query_banned = "SELECT COUNT(*) FROM users WHERE is_banned = 1"
            
            total = self.db.execute_query(query_total, fetch_one=True)[0]
            banned = self.db.execute_query(query_banned, fetch_one=True)[0]
            
            return {
                'total': total,
                'banned': banned,
                'active': total - banned
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات المستخدمين: {e}")
            return {'total': 0, 'banned': 0, 'active': 0}
    
    def get_top_users_by_balance(self, limit: int = 20) -> List[tuple]:
        """جلب أعلى المستخدمين حسب الرصيد"""
        try:
            query = """
                SELECT user_id, balance, created_at, last_active
                FROM users 
                WHERE is_banned = 0
                ORDER BY balance DESC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أعلى المستخدمين: {e}")
            return []
    
    def get_top_users_by_deposit(self, limit: int = 10) -> List[tuple]:
        """جلب أعلى المودعين"""
        try:
            query = """
                SELECT user_id, SUM(amount) as total_deposit
                FROM transactions 
                WHERE type = 'charge' AND status = 'approved'
                GROUP BY user_id
                ORDER BY total_deposit DESC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أعلى المودعين: {e}")
            return []
    
    def ban_user(self, user_id: int, reason: str = "", ban_until: str = None, admin_id: int = 8146077656) -> bool:
        """حظر مستخدم"""
        try:
            query = """
                UPDATE users 
                SET is_banned = 1, ban_reason = ?, ban_until = ?
                WHERE user_id = ?
            """
            self.db.execute_query(query, (reason, ban_until, user_id))
            
            logger.info(f"✅ تم حظر المستخدم {user_id} بواسطة {admin_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في حظر المستخدم: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """فك حظر مستخدم"""
        try:
            query = """
                UPDATE users 
                SET is_banned = 0, ban_reason = NULL, ban_until = NULL
                WHERE user_id = ?
            """
            self.db.execute_query(query, (user_id,))
            
            logger.info(f"✅ تم فك حظر المستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في فك حظر المستخدم: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """حذف مستخدم"""
        try:
            # حذف البيانات المرتبطة أولاً
            queries = [
                "DELETE FROM sessions WHERE user_id = ?",
                "DELETE FROM ichancy_accounts WHERE user_id = ?", 
                "DELETE FROM admins WHERE user_id = ?",
                "DELETE FROM referrals WHERE referrer_id = ? OR referred_id = ?",
                "DELETE FROM users WHERE user_id = ?"
            ]
            
            for query in queries:
                self.db.execute_query(query, (user_id, user_id) if 'referrals' in query else (user_id,))
            
            # مسح الكاش
            if user_id in self._cache:
                del self._cache[user_id]
            
            logger.info(f"✅ تم حذف المستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في حذف المستخدم: {e}")
            return False
    
    def reset_all_balances(self) -> Dict[str, Any]:
        """تصفير جميع الأرصدة"""
        try:
            query = "UPDATE users SET balance = 0 WHERE is_banned = 0"
            result = self.db.execute_query(query)
            
            affected = result if result else 0
            logger.info(f"✅ تم تصفير أرصدة {affected} مستخدم")
            
            return {'success': True, 'affected': affected}
        except Exception as e:
            logger.error(f"❌ خطأ في تصفير الأرصدة: {e}")
            return {'success': False, 'message': str(e)}
    
    def is_admin(self, user_id: int) -> bool:
        """التحقق إذا كان المستخدم أدمن"""
        if user_id == 8146077656:  # ADMIN_ID
            return True
        
        # التحقق من الكاش أولاً
        if user_id in self._cache:
            return self._cache[user_id]
        
        try:
            query = "SELECT 1 FROM admins WHERE user_id = ?"
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            is_admin = result is not None
            
            # حفظ في الكاش
            self._cache[user_id] = is_admin
            return is_admin
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من الأدمن: {e}")
            return False
    
    def get_all_admins(self) -> List[tuple]:
        """جلب جميع الأدمن"""
        try:
            query = """
                SELECT u.user_id, u.created_at, a.added_at, a.added_by
                FROM admins a
                JOIN users u ON a.user_id = u.user_id
                ORDER BY a.added_at DESC
            """
            return self.db.execute_query(query, fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع الأدمن: {e}")
            return []
    
    def can_manage_admins(self, user_id: int) -> bool:
        """التحقق إذا كان يمكن إدارة الأدمن"""
        return user_id == 8146077656  # المشرف الرئيسي فقط
    
    def add_admin(self, user_id: int, added_by: int = 8146077656) -> Dict[str, Any]:
        """إضافة أدمن جديد"""
        if not self.is_admin(added_by) and added_by != 8146077656:
            return {"success": False, "message": "❌ ليس لديك صلاحية إضافة أدمن"}
        
        if user_id == 8146077656:
            return {"success": False, "message": "❌ المشرف الرئيسي مضاف بالفعل"}
        
        try:
            # التحقق من عدد الأدمن
            admins = self.get_all_admins()
            max_admins = 10  # يمكن جلبها من الإعدادات
            if len(admins) >= max_admins:
                return {"success": False, "message": f"❌ وصلت للحد الأقصى ({max_admins} أدمن)"}
            
            # التحقق إذا كان المستخدم موجوداً
            if not self.get_user(user_id):
                return {"success": False, "message": "❌ المستخدم غير موجود في البوت"}
            
            # التحقق إذا كان أدمن بالفعل
            query_check = "SELECT 1 FROM admins WHERE user_id = ?"
            if self.db.execute_query(query_check, (user_id,), fetch_one=True):
                return {"success": False, "message": "❌ المستخدم أدمن بالفعل"}
            
            # إضافة الأدمن
            query_add = """
                INSERT INTO admins (user_id, added_by, added_at)
                VALUES (?, ?, datetime('now'))
            """
            self.db.execute_query(query_add, (user_id, added_by))
            
            # تحديث الكاش
            self._cache[user_id] = True
            
            logger.info(f"✅ تم إضافة أدمن جديد: {user_id}")
            return {"success": True, "message": f"✅ تم إضافة المستخدم {user_id} كأدمن"}
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة أدمن: {e}")
            return {"success": False, "message": f"❌ خطأ في الإضافة: {str(e)[:100]}"}
    
    def remove_admin(self, user_id: int, removed_by: int = 8146077656) -> Dict[str, Any]:
        """حذف أدمن"""
        if not self.can_manage_admins(removed_by):
            return {"success": False, "message": "❌ ليس لديك صلاحية حذف أدمن"}
        
        if user_id == 8146077656:
            return {"success": False, "message": "❌ لا يمكن حذف المشرف الرئيسي"}
        
        try:
            # التحقق إذا كان أدمن
            if not self.is_admin(user_id):
                return {"success": False, "message": "❌ المستخدم ليس أدمن"}
            
            # حذف الأدمن
            query = "DELETE FROM admins WHERE user_id = ?"
            self.db.execute_query(query, (user_id,))
            
            # تحديث الكاش
            if user_id in self._cache:
                del self._cache[user_id]
            
            logger.info(f"✅ تم حذف أدمن: {user_id}")
            return {"success": True, "message": f"✅ تم حذف المستخدم {user_id} من قائمة الأدمن"}
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف أدمن: {e}")
            return {"success": False, "message": f"❌ خطأ في الحذف: {str(e)[:100]}"}
    
    def send_message_to_user(self, target_id: int, message: str, admin_id: int = 8146077656) -> bool:
        """إرسال رسالة لمستخدم"""
        try:
            # هذه الدالة ستعمل مع البوت في main.py
            # نحتاج فقط لتسجيل العملية
            query = """
                INSERT INTO broadcast_messages (admin_id, message_text, message_type, sent_count, created_at)
                VALUES (?, ?, 'text', 1, datetime('now'))
            """
            self.db.execute_query(query, (admin_id, message))
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الرسالة: {e}")
            return False