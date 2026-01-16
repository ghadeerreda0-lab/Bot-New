"""
خدمة إدارة نظام الإحالات
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ReferralService:
    """خدمة إدارة نظام الإحالات والمكافآت"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_referral_settings(self) -> Dict[str, Any]:
        """جلب إعدادات الإحالات"""
        try:
            query = "SELECT * FROM referral_settings ORDER BY id DESC LIMIT 1"
            result = self.db.execute_query(query, fetch_one=True)
            
            if result:
                return {
                    "commission_rate": result[1],
                    "bonus_amount": result[2],
                    "min_active_referrals": result[3],
                    "min_charge_amount": result[4],
                    "next_distribution": result[5],
                    "updated_at": result[6]
                }
            
            # إعدادات افتراضية
            return {
                "commission_rate": 10,
                "bonus_amount": 2000,
                "min_active_referrals": 5,
                "min_charge_amount": 100000,
                "next_distribution": None,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات الإحالات: {e}")
            return {}
    
    def update_referral_settings(self, commission_rate: int = None, bonus_amount: int = None,
                               min_active_referrals: int = None, min_charge_amount: int = None,
                               next_distribution: str = None) -> bool:
        """تحديث إعدادات الإحالات"""
        try:
            settings = self.get_referral_settings()
            
            # استخدام القيم الحالية إذا لم يتم توفير قيم جديدة
            commission_rate = commission_rate if commission_rate is not None else settings.get('commission_rate', 10)
            bonus_amount = bonus_amount if bonus_amount is not None else settings.get('bonus_amount', 2000)
            min_active_referrals = min_active_referrals if min_active_referrals is not None else settings.get('min_active_referrals', 5)
            min_charge_amount = min_charge_amount if min_charge_amount is not None else settings.get('min_charge_amount', 100000)
            next_distribution = next_distribution if next_distribution is not None else settings.get('next_distribution')
            
            query = """
                INSERT OR REPLACE INTO referral_settings 
                (commission_rate, bonus_amount, min_active_referrals, min_charge_amount, next_distribution, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """
            self.db.execute_query(query, (commission_rate, bonus_amount, min_active_referrals, min_charge_amount, next_distribution))
            
            logger.info("✅ تم تحديث إعدادات الإحالات")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعدادات الإحالات: {e}")
            return False
    
    def get_user_referrals(self, user_id: int) -> List[tuple]:
        """جلب إحالات المستخدم"""
        try:
            query = """
                SELECT r.referred_id, u.created_at, r.amount_charged, r.is_active,
                       (SELECT COALESCE(SUM(amount), 0) FROM transactions 
                        WHERE user_id = r.referred_id AND type = 'charge' AND status = 'approved') as total_charged
                FROM referrals r
                JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
            """
            return self.db.execute_query(query, (user_id,), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحالات المستخدم: {e}")
            return []
    
    def get_top_referrals(self, limit: int = 10) -> List[tuple]:
        """جلب أعلى الإحالات"""
        try:
            query = """
                SELECT r.referrer_id, COUNT(*) as total_refs,
                       SUM(CASE WHEN r.amount_charged >= 10000 THEN 1 ELSE 0 END) as active_refs,
                       SUM(r.commission_earned) as total_commission,
                       (SELECT referral_code FROM users WHERE user_id = r.referrer_id) as referral_code
                FROM referrals r
                GROUP BY r.referrer_id
                ORDER BY total_refs DESC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,), fetch_all=True)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أعلى الإحالات: {e}")
            return []
    
    def calculate_referral_commissions(self) -> List[tuple]:
        """حساب عمولات الإحالات المستحقة"""
        try:
            settings = self.get_referral_settings()
            
            # النظام الأول: نسبة من الإحالات النشطة
            query_system1 = """
                SELECT r.referrer_id, 
                       COUNT(*) as total_active,
                       SUM(r.amount_charged) as total_charged,
                       (SUM(r.amount_charged) * ? / 100) as commission
                FROM referrals r
                WHERE r.is_active = 1 
                AND r.amount_charged >= ?
                GROUP BY r.referrer_id
                HAVING COUNT(*) >= ?
            """
            params1 = (settings['commission_rate'], settings['min_charge_amount'], settings['min_active_referrals'])
            system1_commissions = self.db.execute_query(query_system1, params1, fetch_all=True)
            
            # النظام الثاني: مكافأة ثابتة لكل إحالة نشطة
            query_system2 = """
                SELECT referrer_id, 
                       COUNT(*) as eligible_refs,
                       (COUNT(*) * ?) as bonus
                FROM referrals 
                WHERE is_active = 1 
                AND amount_charged >= 10000
                GROUP BY referrer_id
            """
            params2 = (settings['bonus_amount'],)
            system2_bonuses = self.db.execute_query(query_system2, params2, fetch_all=True)
            
            # دمج النتائج
            commissions = {}
            
            for ref_id, total_active, total_charged, commission in system1_commissions:
                if ref_id not in commissions:
                    commissions[ref_id] = 0
                commissions[ref_id] += commission
            
            for ref_id, eligible_refs, bonus in system2_bonuses:
                if ref_id not in commissions:
                    commissions[ref_id] = 0
                commissions[ref_id] += bonus
            
            # تحويل إلى قائمة
            result = [(ref_id, int(amount)) for ref_id, amount in commissions.items() if amount > 0]
            return result
            
        except Exception as e:
            logger.error(f"❌ خطأ في حساب عمولات الإحالات: {e}")
            return []
    
    def distribute_referral_commissions(self) -> Dict[str, Any]:
        """توزيع عمولات الإحالات تلقائياً"""
        try:
            commissions = self.calculate_referral_commissions()
            if not commissions:
                return {"success": False, "message": "⚠️ لا توجد عمولات مستحقة للتوزيع", "distributed": 0}
            
            total_distributed = 0
            distributed_users = []
            
            from services.user_service import UserService
            # Note: We'll need to pass user_service or handle balance updates differently
            
            for user_id, amount in commissions:
                # هذا الجزء سيتم إكماله مع integration كامل
                distributed_users.append((user_id, amount))
                total_distributed += amount
            
            logger.info(f"✅ تم حساب عمولات الإحالات: {total_distributed:,} ليرة على {len(distributed_users)} مستخدم")
            return {
                "success": True,
                "message": f"✅ تم حساب {total_distributed:,} ليرة لـ {len(distributed_users)} مستخدم",
                "distributed": total_distributed,
                "users": distributed_users
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في توزيع عمولات الإحالات: {e}")
            return {"success": False, "message": f"❌ خطأ في التوزيع: {str(e)[:100]}"}
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """إضافة إحالة جديدة"""
        try:
            # التحقق من عدم تكرار الإحالة
            query_check = "SELECT 1 FROM referrals WHERE referred_id = ?"
            existing = self.db.execute_query(query_check, (referred_id,), fetch_one=True)
            
            if existing:
                return False
            
            # إضافة الإحالة
            query_add = """
                INSERT INTO referrals (referrer_id, referred_id, created_at)
                VALUES (?, ?, datetime('now'))
            """
            self.db.execute_query(query_add, (referrer_id, referred_id))
            
            logger.info(f"✅ تم إضافة إحالة: {referrer_id} ← {referred_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة إحالة: {e}")
            return False
    
    def update_referral_activity(self, referred_id: int, amount_charged: int) -> bool:
        """تحديث نشاط الإحالة"""
        try:
            query = """
                UPDATE referrals 
                SET amount_charged = amount_charged + ?, 
                    is_active = CASE WHEN amount_charged + ? >= 10000 THEN 1 ELSE is_active END
                WHERE referred_id = ?
            """
            self.db.execute_query(query, (amount_charged, amount_charged, referred_id))
            
            logger.info(f"✅ تم تحديث إحالة المستخدم {referred_id} بمبلغ {amount_charged}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث نشاط الإحالة: {e}")
            return False