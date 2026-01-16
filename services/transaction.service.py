"""
خدمة إدارة المعاملات المالية
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TransactionService:
    """خدمة إدارة جميع المعاملات المالية"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def approve_transaction(self, transaction_id: int, admin_id: int = 8146077656) -> Dict[str, Any]:
        """الموافقة على معاملة"""
        try:
            # جلب تفاصيل المعاملة
            query_get = """
                SELECT t.user_id, t.amount, t.type, u.balance
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.id = ? AND t.status = 'pending'
            """
            result = self.db.execute_query(query_get, (transaction_id,), fetch_one=True)
            
            if not result:
                return {"success": False, "message": "⚠️ المعاملة غير موجودة أو تمت معالجتها"}
            
            user_id, amount, type_, current_balance = result
            
            if type_ == 'charge':
                # إضافة الرصيد للمستخدم
                new_balance = current_balance + amount
                query_update_user = "UPDATE users SET balance = ? WHERE user_id = ?"
                self.db.execute_query(query_update_user, (new_balance, user_id))
                
                message = f"✅ تم قبول طلب الشحن! تم إضافة {amount:,} ليرة إلى رصيدك"
                
            elif type_ == 'withdraw':
                # للسحب، الرصيد تم خصمه مسبقاً، فقط نغير الحالة
                message = f"✅ تم قبول طلب السحب! سيتم تحويل {amount:,} ليرة قريباً"
            
            else:
                return {"success": False, "message": "❌ نوع معاملة غير معروف"}
            
            # تحديث حالة المعاملة
            query_update_tx = "UPDATE transactions SET status = 'approved' WHERE id = ?"
            self.db.execute_query(query_update_tx, (transaction_id,))
            
            logger.info(f"✅ تمت الموافقة على المعاملة #{transaction_id} بواسطة {admin_id}")
            
            return {
                "success": True,
                "message": "✅ تمت الموافقة على المعاملة",
                "user_id": user_id,
                "amount": amount,
                "type": type_,
                "notification": message
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في الموافقة على المعاملة: {e}")
            return {"success": False, "message": f"❌ خطأ في المعالجة: {str(e)[:100]}"}
    
    def reject_transaction(self, transaction_id: int, admin_id: int = 8146077656) -> Dict[str, Any]:
        """رفض معاملة"""
        try:
            # جلب تفاصيل المعاملة
            query_get = """
                SELECT t.user_id, t.amount, t.type, u.balance
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.id = ? AND t.status = 'pending'
            """
            result = self.db.execute_query(query_get, (transaction_id,), fetch_one=True)
            
            if not result:
                return {"success": False, "message": "⚠️ المعاملة غير موجودة أو تمت معالجتها"}
            
            user_id, amount, type_, current_balance = result
            
            if type_ == 'withdraw':
                # إرجاع الرصيد للمستخدم إذا كان سحب مرفوض
                new_balance = current_balance + amount
                query_update_user = "UPDATE users SET balance = ? WHERE user_id = ?"
                self.db.execute_query(query_update_user, (new_balance, user_id))
                
                message = f"❌ تم رفض طلب السحب! تم إرجاع {amount:,} ليرة إلى رصيدك"
            else:
                message = f"❌ تم رفض طلب الشحن بمبلغ {amount:,} ليرة"
            
            # تحديث حالة المعاملة
            query_update_tx = "UPDATE transactions SET status = 'rejected' WHERE id = ?"
            self.db.execute_query(query_update_tx, (transaction_id,))
            
            logger.info(f"❌ تم رفض المعاملة #{transaction_id} بواسطة {admin_id}")
            
            return {
                "success": True,
                "message": "❌ تم رفض المعاملة",
                "user_id": user_id,
                "amount": amount,
                "type": type_,
                "notification": message
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في رفض المعاملة: {e}")
            return {"success": False, "message": f"❌ خطأ في المعالجة: {str(e)[:100]}"}
    
    def get_pending_transactions(self, limit: int = 50, offset: int = 0) -> List[tuple]:
        """جلب المعاملات المعلقة"""
        try:
            query = """
                SELECT t.id, t.user_id, t.type, t.amount, t.payment_method, t.created_at, t.notes,
                       u.balance as user_balance
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.status = 'pending'
                ORDER BY t.created_at ASC
                LIMIT ? OFFSET ?
            """
            return self.db.execute_query(query, (limit, offset), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المعاملات المعلقة: {e}")
            return []
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """جلب إحصائيات المعاملات"""
        try:
            # إجمالي الإيداعات
            query_total_deposit = """
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE type = 'charge' AND status = 'approved'
            """
            total_deposit = self.db.execute_query(query_total_deposit, fetch_one=True)[0] or 0
            
            # إجمالي السحوبات
            query_total_withdraw = """
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE type = 'withdraw' AND status = 'approved'
            """
            total_withdraw = self.db.execute_query(query_total_withdraw, fetch_one=True)[0] or 0
            
            # عدد المعاملات المعلقة
            query_pending_count = "SELECT COUNT(*) FROM transactions WHERE status = 'pending'"
            pending_count = self.db.execute_query(query_pending_count, fetch_one=True)[0] or 0
            
            # عدد المعاملات اليوم
            today = datetime.now().strftime("%Y-%m-%d")
            query_today_count = "SELECT COUNT(*) FROM transactions WHERE date(created_at) = ?"
            today_count = self.db.execute_query(query_today_count, (today,), fetch_one=True)[0] or 0
            
            # أعلى معاملة
            query_highest = """
                SELECT MAX(amount) FROM transactions 
                WHERE status = 'approved' AND type = 'charge'
            """
            highest_deposit = self.db.execute_query(query_highest, fetch_one=True)[0] or 0
            
            return {
                "total_deposit": total_deposit,
                "total_withdraw": total_withdraw,
                "net_flow": total_deposit - total_withdraw,
                "pending_count": pending_count,
                "today_count": today_count,
                "highest_deposit": highest_deposit,
                "average_deposit": total_deposit / (today_count if today_count > 0 else 1)
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات المعاملات: {e}")
            return {}
    
    def create_transaction_log(self, user_id: int, action: str, details: str, 
                             admin_id: int = None) -> bool:
        """إنشاء سجل للمعاملات (للتدقيق)"""
        try:
            query = """
                INSERT INTO transaction_logs (user_id, action, details, admin_id, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """
            self.db.execute_query(query, (user_id, action, details, admin_id))
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء سجل المعاملة: {e}")
            return False