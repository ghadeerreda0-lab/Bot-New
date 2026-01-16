"""
خدمة إدارة عمليات الدفع والشحن
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class PaymentService:
    """خدمة إدارة جميع عمليات الدفع"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_payment_methods(self) -> Dict[str, Dict]:
        """جلب جميع طرق الدفع"""
        return {
            'syriatel_cash': {
                'name': '📱 سيرياتيل كاش',
                'min_amount': 1000,
                'max_amount': 50000,
                'enabled': self.get_setting('syriatel_cash_enabled') == 'true',
                'visible': self.get_setting('syriatel_cash_visible') == 'true'
            },
            'sham_cash': {
                'name': '💰 شام كاش',
                'min_amount': 1000,
                'max_amount': 50000,
                'enabled': self.get_setting('sham_cash_enabled') == 'true',
                'visible': self.get_setting('sham_cash_visible') == 'true'
            },
            'sham_cash_usd': {
                'name': '💵 شام كاش دولار',
                'min_amount': 10,
                'max_amount': 500,
                'enabled': self.get_setting('sham_cash_usd_enabled') == 'true',
                'visible': self.get_setting('sham_cash_usd_visible') == 'true'
            }
        }
    
    def get_setting(self, key: str, default: str = None) -> str:
        """جلب إعداد من النظام"""
        try:
            query = "SELECT value FROM system_settings WHERE key = ?"
            result = self.db.execute_query(query, (key,), fetch_one=True)
            return result[0] if result else default
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإعداد {key}: {e}")
            return default
    
    def update_setting(self, key: str, value: str, admin_id: int = 8146077656, reason: str = "") -> bool:
        """تحديث إعداد النظام"""
        try:
            old_value = self.get_setting(key)
            
            query = """
                INSERT OR REPLACE INTO system_settings (key, value, updated_at, updated_by)
                VALUES (?, ?, datetime('now'), ?)
            """
            self.db.execute_query(query, (key, value, admin_id))
            
            logger.info(f"✅ تم تحديث الإعداد: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الإعداد {key}: {e}")
            return False
    
    def check_payment_enabled(self, payment_method: str) -> bool:
        """التحقق من تفعيل طريقة الدفع"""
        methods = self.get_payment_methods()
        if payment_method not in methods:
            return False
        
        method_info = methods[payment_method]
        return method_info['enabled'] and method_info['visible']
    
    def get_available_code_for_amount(self, amount: int) -> Dict[str, Any]:
        """العثور على كود متاح للمبلغ"""
        try:
            query = """
                SELECT id, code_number, current_amount 
                FROM syriatel_codes 
                WHERE is_active = 1 
                AND (5400 - current_amount) >= ?
                ORDER BY current_amount ASC
                LIMIT 1
            """
            result = self.db.execute_query(query, (amount,), fetch_one=True)
            
            if result:
                return {
                    "success": True,
                    "code_id": result[0],
                    "code_number": result[1],
                    "current_amount": result[2],
                    "available": 5400 - result[2]
                }
            else:
                # جلب أكبر كود متاح
                query_max = """
                    SELECT MAX(5400 - current_amount) as max_available
                    FROM syriatel_codes 
                    WHERE is_active = 1
                """
                max_result = self.db.execute_query(query_max, fetch_one=True)
                max_available = max_result[0] if max_result and max_result[0] else 0
                
                return {
                    "success": False,
                    "max_available": max_available,
                    "message": f"❌ لا يوجد كود يمكنه استيعاب {amount:,} ليرة"
                }
        except Exception as e:
            logger.error(f"❌ خطأ في البحث عن كود: {e}")
            return {"success": False, "message": str(e)}
    
    def fill_code_with_amount(self, code_id: int, user_id: int, amount: int) -> Dict[str, Any]:
        """تعبئة الكود بالمبلغ"""
        try:
            # التحقق من توفر المساحة في الكود
            query_check = """
                SELECT current_amount FROM syriatel_codes WHERE id = ? AND is_active = 1
            """
            result = self.db.execute_query(query_check, (code_id,), fetch_one=True)
            
            if not result:
                return {"success": False, "message": "❌ الكود غير موجود أو غير نشط"}
            
            current_amount = result[0]
            if (5400 - current_amount) < amount:
                return {"success": False, "message": "❌ المساحة غير كافية في الكود"}
            
            # تحديث الكود
            new_amount = current_amount + amount
            query_update = """
                UPDATE syriatel_codes 
                SET current_amount = ?, last_used = datetime('now'), usage_count = usage_count + 1
                WHERE id = ?
            """
            self.db.execute_query(query_update, (new_amount, code_id))
            
            # تسجيل العملية
            query_log = """
                INSERT INTO code_fill_logs (code_id, user_id, amount, remaining_in_code, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """
            self.db.execute_query(query_log, (code_id, user_id, amount, 5400 - new_amount))
            
            logger.info(f"✅ تم تعبئة الكود {code_id} بمبلغ {amount} ليرة")
            return {"success": True, "new_amount": new_amount}
            
        except Exception as e:
            logger.error(f"❌ خطأ في تعبئة الكود: {e}")
            return {"success": False, "message": str(e)}
    
    def add_transaction(self, user_id: int, type_: str, amount: int, 
                       payment_method: str = None, transaction_id: str = None,
                       account_number: str = "", notes: str = "") -> tuple:
        """إضافة معاملة جديدة"""
        try:
            # جلب رقم الطلب الشهري
            month = datetime.now().month
            year = datetime.now().year
            
            query_counter = """
                INSERT OR REPLACE INTO monthly_counter (month, year, payment_method, counter)
                VALUES (?, ?, ?, COALESCE((SELECT counter FROM monthly_counter 
                         WHERE month = ? AND year = ? AND payment_method = ?), 0) + 1)
            """
            self.db.execute_query(query_counter, (month, year, payment_method, month, year, payment_method))
            
            # جلب رقم الطلب الجديد
            query_get_counter = """
                SELECT counter FROM monthly_counter 
                WHERE month = ? AND year = ? AND payment_method = ?
            """
            counter_result = self.db.execute_query(query_get_counter, (month, year, payment_method), fetch_one=True)
            order_number = counter_result[0] if counter_result else 1
            
            # إضافة المعاملة
            query_transaction = """
                INSERT INTO transactions (user_id, type, amount, payment_method, transaction_id, 
                                        account_number, status, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'), ?)
            """
            tx_id = self.db.execute_query(query_transaction, 
                                         (user_id, type_, amount, payment_method, 
                                          transaction_id, account_number, notes))
            
            order_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"✅ تم إضافة معاملة #{tx_id} للمستخدم {user_id}")
            
            return tx_id, order_number, order_datetime
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة معاملة: {e}")
            return None, 0, ""
    
    def get_transaction(self, transaction_id: int) -> Optional[Dict]:
        """جلب تفاصيل معاملة"""
        try:
            query = """
                SELECT t.id, t.user_id, t.type, t.amount, t.payment_method, t.transaction_id,
                       t.account_number, t.status, t.created_at, t.notes,
                       u.balance as user_balance
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.id = ?
            """
            result = self.db.execute_query(query, (transaction_id,), fetch_one=True)
            
            if result:
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'type': result[2],
                    'amount': result[3],
                    'payment_method': result[4],
                    'transaction_id': result[5],
                    'account_number': result[6],
                    'status': result[7],
                    'created_at': result[8],
                    'notes': result[9],
                    'user_balance': result[10]
                }
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المعاملة: {e}")
            return None
    
    def update_transaction_status(self, transaction_id: int, status: str, 
                                 admin_id: int = 8146077656) -> bool:
        """تحديث حالة المعاملة"""
        try:
            query = """
                UPDATE transactions 
                SET status = ? 
                WHERE id = ?
            """
            self.db.execute_query(query, (status, transaction_id))
            
            logger.info(f"✅ تم تحديث حالة المعاملة #{transaction_id} إلى {status}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث حالة المعاملة: {e}")
            return False
    
    def get_user_transactions(self, user_id: int, limit: int = 50, offset: int = 0) -> List[tuple]:
        """جلب معاملات المستخدم"""
        try:
            query = """
                SELECT id, type, amount, payment_method, status, created_at, notes
                FROM transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.db.execute_query(query, (user_id, limit, offset), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب معاملات المستخدم: {e}")
            return []
    
    def get_deposit_report(self, payment_method: str = None, date_str: str = None) -> Dict[str, Any]:
        """جلب تقرير عمليات الشحن"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            query_base = """
                SELECT t.id, t.user_id, t.amount, t.payment_method, t.created_at, t.status,
                       u.balance as user_balance
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.type = 'charge' AND date(t.created_at) = ?
            """
            params = [date_str]
            
            if payment_method:
                query_base += " AND t.payment_method = ?"
                params.append(payment_method)
            
            query_base += " ORDER BY t.created_at DESC"
            transactions = self.db.execute_query(query_base, tuple(params), fetch_all=True)
            
            # حساب الإجماليات
            query_total = """
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM transactions 
                WHERE type = 'charge' AND date(created_at) = ?
            """
            total_params = [date_str]
            
            if payment_method:
                query_total += " AND payment_method = ?"
                total_params.append(payment_method)
            
            total_result = self.db.execute_query(query_total, tuple(total_params), fetch_one=True)
            total_amount, total_count = total_result if total_result else (0, 0)
            
            return {
                "transactions": transactions,
                "total_amount": total_amount,
                "total_count": total_count,
                "payment_method": payment_method or "جميع الطرق",
                "date": date_str
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تقرير الشحن: {e}")
            return {"transactions": [], "total_amount": 0, "total_count": 0, "date": date_str}
    
    def get_withdraw_report(self, date_str: str = None) -> Dict[str, Any]:
        """جلب تقرير عمليات السحب"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            query = """
                SELECT t.id, t.user_id, t.amount, t.payment_method, t.created_at, t.status,
                       u.balance as user_balance
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.type = 'withdraw' AND date(t.created_at) = ?
                ORDER BY t.created_at DESC
            """
            transactions = self.db.execute_query(query, (date_str,), fetch_all=True)
            
            query_total = """
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM transactions 
                WHERE type = 'withdraw' AND date(created_at) = ?
            """
            total_result = self.db.execute_query(query_total, (date_str,), fetch_one=True)
            total_amount, total_count = total_result if total_result else (0, 0)
            
            return {
                "transactions": transactions,
                "total_amount": total_amount,
                "total_count": total_count,
                "date": date_str
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تقرير السحب: {e}")
            return {"transactions": [], "total_amount": 0, "total_count": 0, "date": date_str}
    
    def get_daily_report(self, date_str: str = None) -> Dict[str, Any]:
        """جلب التقرير اليومي"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # إحصائيات المستخدمين
            query_new_users = "SELECT COUNT(*) FROM users WHERE date(created_at) = ?"
            new_users = self.db.execute_query(query_new_users, (date_str,), fetch_one=True)[0] or 0
            
            query_total_users = "SELECT COUNT(*) FROM users"
            total_users = self.db.execute_query(query_total_users, fetch_one=True)[0] or 0
            
            query_active_users = """
                SELECT COUNT(DISTINCT user_id) FROM transactions 
                WHERE date(created_at) = ?
            """
            active_users = self.db.execute_query(query_active_users, (date_str,), fetch_one=True)[0] or 0
            
            # إحصائيات مالية
            query_total_deposit = """
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE type = 'charge' AND status = 'approved' AND date(created_at) = ?
            """
            total_deposit = self.db.execute_query(query_total_deposit, (date_str,), fetch_one=True)[0] or 0
            
            query_total_withdraw = """
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE type = 'withdraw' AND status = 'approved' AND date(created_at) = ?
            """
            total_withdraw = self.db.execute_query(query_total_withdraw, (date_str,), fetch_one=True)[0] or 0
            
            query_total_transactions = """
                SELECT COUNT(*) FROM transactions WHERE date(created_at) = ?
            """
            total_transactions = self.db.execute_query(query_total_transactions, (date_str,), fetch_one=True)[0] or 0
            
            query_pending_transactions = """
                SELECT COUNT(*) FROM transactions WHERE status = 'pending' AND date(created_at) = ?
            """
            pending_transactions = self.db.execute_query(query_pending_transactions, (date_str,), fetch_one=True)[0] or 0
            
            # إحصائيات الإحالات
            query_new_referrals = "SELECT COUNT(*) FROM referrals WHERE date(created_at) = ?"
            new_referrals = self.db.execute_query(query_new_referrals, (date_str,), fetch_one=True)[0] or 0
            
            # إحصائيات الأكواد
            query_active_codes = "SELECT COUNT(*) FROM syriatel_codes WHERE is_active = 1"
            active_codes = self.db.execute_query(query_active_codes, fetch_one=True)[0] or 0
            
            query_used_capacity = "SELECT SUM(current_amount) FROM syriatel_codes WHERE is_active = 1"
            used_capacity = self.db.execute_query(query_used_capacity, fetch_one=True)[0] or 0
            
            total_capacity = active_codes * 5400
            fill_percentage = round((used_capacity / total_capacity * 100), 2) if total_capacity > 0 else 0
            
            return {
                "date": date_str,
                "new_users": new_users,
                "total_users": total_users,
                "active_users": active_users,
                "total_deposit": total_deposit,
                "total_withdraw": total_withdraw,
                "total_transactions": total_transactions,
                "pending_transactions": pending_transactions,
                "new_referrals": new_referrals,
                "active_codes": active_codes,
                "used_capacity": used_capacity,
                "total_capacity": total_capacity,
                "fill_percentage": fill_percentage,
                "net_flow": total_deposit - total_withdraw
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب التقرير اليومي: {e}")
            return None