"""
نظام الدفع والمعاملات المالية
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import asyncio

from sqlalchemy.orm import Session
from database.models import (
    User, Transaction, PaymentMethod, 
    SyriatelCode, Bonus, GiftCode
)
from config import Config
from utils.security import SecurityUtils

logger = logging.getLogger(__name__)

class PaymentProcessor:
    def __init__(self):
        self.rates_cache = {}
        self.last_rate_update = None
    
    async def process_deposit(
        self,
        db: Session,
        user_id: int,
        amount: float,
        payment_method_id: int,
        transaction_code: str = None,
        admin_id: int = None
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """معالجة عملية إيداع"""
        try:
            # الحصول على المستخدم
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "المستخدم غير موجود", None
            
            # الحصول على طريقة الدفع
            method = db.query(PaymentMethod).filter(
                PaymentMethod.id == payment_method_id,
                PaymentMethod.is_active == True
            ).first()
            
            if not method:
                return False, "طريقة الدفع غير متاحة", None
            
            # التحقق من الحدود
            if amount < method.min_amount:
                return False, f"المبلغ أقل من الحد الأدنى ({method.min_amount:,.0f})", None
            
            if amount > method.max_amount:
                return False, f"المبلغ أعلى من الحد الأقصى ({method.max_amount:,.0f})", None
            
            # حساب العمولة
            fee = self.calculate_fee(amount, method)
            net_amount = amount - fee
            
            # حساب البونص
            bonus = await self.calculate_bonus(db, amount, payment_method_id, user_id)
            total_amount = net_amount + bonus
            
            # إنشاء المعاملة
            transaction = Transaction(
                user_id=user_id,
                transaction_type="deposit",
                amount=amount,
                fee=fee,
                net_amount=total_amount,
                payment_method=method.name,
                transaction_code=transaction_code,
                status="pending",
                admin_id=admin_id,
                auto_verified=False,
                created_at=datetime.utcnow()
            )
            
            db.add(transaction)
            db.flush()  # للحصول على ID
            
            # تحديث رصيد المستخدم (مؤقتاً)
            user.balance += total_amount
            
            # إذا كانت العملية مؤكدة فوراً
            if transaction_code and self.verify_transaction_code(transaction_code, method.name):
                transaction.status = "completed"
                transaction.auto_verified = True
                transaction.completed_at = datetime.utcnow()
                db.commit()
                
                # إشعار المستخدم
                await self.notify_deposit_success(user, transaction, bonus)
                
                return True, f"تم الإيداع بنجاح! +{bonus:,.0f} مكافأة", transaction
            else:
                transaction.status = "pending"
                db.commit()
                
                # إشعار الإدمن بطلب إيداع جديد
                await self.notify_admin_pending_deposit(transaction)
                
                return True, "تم إرسال طلب الإيداع. في انتظار الموافقة.", transaction
                
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في process_deposit: {e}")
            return False, "حدث خطأ في النظام", None
    
    async def process_withdrawal(
        self,
        db: Session,
        user_id: int,
        amount: float,
        payment_method_id: int,
        account_info: str,
        admin_id: int = None
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """معالجة عملية سحب"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "المستخدم غير موجود", None
            
            # التحقق من الرصيد
            if user.balance < amount:
                return False, "رصيدك غير كافي", None
            
            method = db.query(PaymentMethod).filter(
                PaymentMethod.id == payment_method_id,
                PaymentMethod.is_active == True
            ).first()
            
            if not method:
                return False, "طريقة السحب غير متاحة", None
            
            # حساب العمولة
            fee = self.calculate_fee(amount, method)
            net_amount = amount - fee
            
            # إذا كانت نسبة العمولة 0، استخدم الإعداد العام
            if fee == 0 and Config.WITHDRAWAL_FEE > 0:
                fee = amount * (Config.WITHDRAWAL_FEE / 100)
                net_amount = amount - fee
            
            # إنشاء المعاملة
            transaction = Transaction(
                user_id=user_id,
                transaction_type="withdraw",
                amount=amount,
                fee=fee,
                net_amount=net_amount,
                payment_method=method.name,
                transaction_code=None,
                status="pending",
                admin_id=admin_id,
                auto_verified=False,
                notes=f"رقم الحساب: {account_info}",
                created_at=datetime.utcnow()
            )
            
            db.add(transaction)
            
            # خصم الرصيد مؤقتاً
            user.balance -= amount
            
            # السحب دائماً يحتاج موافقة يدوية
            transaction.status = "pending"
            db.commit()
            
            # إشعار الإدمن بطلب سحب جديد
            await self.notify_admin_pending_withdrawal(transaction, account_info)
            
            return True, "تم إرسال طلب السحب. في انتظار الموافقة.", transaction
            
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في process_withdrawal: {e}")
            return False, "حدث خطأ في النظام", None
    
    def calculate_fee(self, amount: float, method: PaymentMethod) -> float:
        """حساب العمولة"""
        fee = 0
        
        # العمولة النسبية
        if method.fee_percentage > 0:
            fee += amount * (method.fee_percentage / 100)
        
        # العمولة الثابتة
        if method.fee_fixed > 0:
            fee += method.fee_fixed
        
        return round(fee, 2)
    
    async def calculate_bonus(
        self, 
        db: Session, 
        amount: float, 
        payment_method_id: int, 
        user_id: int
    ) -> float:
        """حساب البونص"""
        try:
            bonus_amount = 0
            
            # البحث عن بونصات فعالة
            bonuses = db.query(Bonus).filter(
                Bonus.is_active == True,
                Bonus.expires_at > datetime.utcnow()
            ).all()
            
            for bonus in bonuses:
                # البونص العادي
                if bonus.bonus_type == "normal" and bonus.payment_method_id == payment_method_id:
                    bonus_amount = amount * (bonus.percentage / 100)
                    break
                
                # البونص المشروط
                elif bonus.bonus_type == "conditional" and amount >= bonus.min_amount:
                    if bonus.payment_method_id is None or bonus.payment_method_id == payment_method_id:
                        bonus_amount = amount * (bonus.percentage / 100)
                        break
            
            return round(bonus_amount, 2)
            
        except Exception as e:
            logger.error(f"خطأ في calculate_bonus: {e}")
            return 0
    
    def verify_transaction_code(self, code: str, method_name: str) -> bool:
        """التحقق من رقم العملية"""
        # هذه دمية - سيتم استبدالها بالتحقق الفعلي من SMS
        if method_name == "syriatel_cash":
            # التحقق من صحة تنسيق رقم عملية سيرياتيل
            return len(code) >= 6 and code.isdigit()
        elif method_name == "cham_cash":
            # التحقق من صحة تنسيق رقم عملية شام
            return len(code) >= 8 and code.isalnum()
        return True
    
    async def get_suitable_syriatel_code(
        self, 
        db: Session, 
        amount: float
    ) -> Optional[SyriatelCode]:
        """الحصول على كود سيرياتيل مناسب للمبلغ"""
        try:
            # البحث عن كود متاح
            code = db.query(SyriatelCode).filter(
                SyriatelCode.is_active == True,
                (SyriatelCode.max_balance - SyriatelCode.current_balance) >= amount
            ).order_by(SyriatelCode.current_balance).first()
            
            return code
        except Exception as e:
            logger.error(f"خطأ في get_suitable_syriatel_code: {e}")
            return None
    
    async def update_syriatel_code_balance(
        self, 
        db: Session, 
        code_id: int, 
        amount: float
    ) -> bool:
        """تحديث رصيد كود سيرياتيل"""
        try:
            code = db.query(SyriatelCode).filter(SyriatelCode.id == code_id).first()
            if not code:
                return False
            
            code.current_balance += amount
            code.last_used = datetime.utcnow()
            
            # إذا وصل الرصيد للحد الأقصى، تعطيل الكود
            if code.current_balance >= code.max_balance:
                code.is_active = False
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في update_syriatel_code_balance: {e}")
            return False
    
    async def reset_syriatel_codes(self, db: Session) -> int:
        """تصفير جميع أكواد سيرياتيل"""
        try:
            count = db.query(SyriatelCode).filter(
                SyriatelCode.is_active == True
            ).update({
                "current_balance": 0,
                "is_active": True,
                "last_used": None
            })
            
            db.commit()
            logger.info(f"تم تصفير {count} كود سيرياتيل")
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في reset_syriatel_codes: {e}")
            return 0
    
    async def process_gift_code(
        self,
        db: Session,
        user_id: int,
        code: str
    ) -> Tuple[bool, str, Optional[float]]:
        """معالجة كود هدية"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "المستخدم غير موجود", None
            
            # البحث عن الكود
            gift_code = db.query(GiftCode).filter(
                GiftCode.code == code.upper(),
                GiftCode.is_active == True
            ).first()
            
            if not gift_code:
                return False, "كود الهدية غير صالح", None
            
            # التحقق من الصلاحية
            if gift_code.expires_at and gift_code.expires_at < datetime.utcnow():
                return False, "كود الهدية منتهي الصلاحية", None
            
            # التحقق من عدد الاستخدامات
            if gift_code.used_count >= gift_code.max_uses:
                return False, "تم استخدام هذا الكود مسبقاً", None
            
            # تحديث الكود
            gift_code.used_count += 1
            if gift_code.used_count >= gift_code.max_uses:
                gift_code.is_active = False
            
            # تحديث رصيد المستخدم
            user.balance += gift_code.amount
            
            # تسجيل المعاملة
            transaction = Transaction(
                user_id=user_id,
                transaction_type="bonus",
                amount=gift_code.amount,
                fee=0,
                net_amount=gift_code.amount,
                payment_method="gift_code",
                status="completed",
                auto_verified=True,
                notes=f"كود هدية: {code}",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            db.add(transaction)
            db.commit()
            
            return True, f"تم إضافة {gift_code.amount:,.0f} ليرة إلى رصيدك", gift_code.amount
            
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في process_gift_code: {e}")
            return False, "حدث خطأ في النظام", None
    
    async def process_gift_balance(
        self,
        db: Session,
        sender_id: int,
        receiver_telegram_id: int,
        amount: float
    ) -> Tuple[bool, str]:
        """معالجة إهداء رصيد"""
        try:
            # التحقق من المرسل
            sender = db.query(User).filter(User.id == sender_id).first()
            if not sender or sender.balance < amount:
                return False, "رصيدك غير كافي"
            
            # البحث عن المستقبل
            receiver = db.query(User).filter(User.telegram_id == receiver_telegram_id).first()
            if not receiver:
                return False, "المستخدم المستقبل غير موجود"
            
            # منع الإهداء للنفس
            if sender.id == receiver.id:
                return False, "لا يمكن إهداء الرصيد لنفسك"
            
            # حساب العمولة
            fee_percentage = self.get_gift_fee_percentage()
            fee = amount * (fee_percentage / 100)
            net_amount = amount - fee
            
            # خصم من المرسل
            sender.balance -= amount
            
            # إضافة للمستقبل
            receiver.balance += net_amount
            
            # تسجيل المعاملة
            gift_transaction = GiftTransaction(
                sender_id=sender.id,
                receiver_id=receiver.id,
                amount=amount,
                fee=fee,
                created_at=datetime.utcnow()
            )
            
            db.add(gift_transaction)
            db.commit()
            
            # إشعار كلا المستخدمين
            await self.notify_gift_sent(sender, receiver, amount, net_amount)
            await self.notify_gift_received(receiver, sender, amount, net_amount)
            
            return True, f"تم إرسال {net_amount:,.0f} ليرة للمستخدم (خصم {fee:,.0f} ليرة عمولة)"
            
        except Exception as e:
            db.rollback()
            logger.error(f"خطأ في process_gift_balance: {e}")
            return False, "حدث خطأ في النظام"
    
    def get_gift_fee_percentage(self) -> float:
        """الحصول على نسبة عمولة الإهداء"""
        # يمكن جلبها من قاعدة البيانات
        return 5.0  # 5% افتراضياً
    
    async def notify_deposit_success(
        self, 
        user: User, 
        transaction: Transaction,
        bonus: float = 0
    ):
        """إشعار بنجاح الإيداع"""
        try:
            # سيتم تنفيذ هذا في الجزء الخاص بالإشعارات
            pass
        except Exception as e:
            logger.error(f"خطأ في notify_deposit_success: {e}")
    
    async def notify_admin_pending_deposit(self, transaction: Transaction):
        """إشعار الإدمن بطلب إيداع جديد"""
        try:
            # سيتم تنفيذ هذا في الجزء الخاص بالإشعارات
            pass
        except Exception as e:
            logger.error(f"خطأ في notify_admin_pending_deposit: {e}")
    
    async def notify_admin_pending_withdrawal(
        self, 
        transaction: Transaction, 
        account_info: str
    ):
        """إشعار الإدمن بطلب سحب جديد"""
        try:
            # سيتم تنفيذ هذا في الجزء الخاص بالإشعارات
            pass
        except Exception as e:
            logger.error(f"خطأ في notify_admin_pending_withdrawal: {e}")
    
    async def notify_gift_sent(
        self, 
        sender: User, 
        receiver: User, 
        amount: float, 
        net_amount: float
    ):
        """إشعار المرسل بإرسال الهدية"""
        try:
            # سيتم تنفيذ هذا في الجزء الخاص بالإشعارات
            pass
        except Exception as e:
            logger.error(f"خطأ في notify_gift_sent: {e}")
    
    async def notify_gift_received(
        self, 
        receiver: User, 
        sender: User, 
        amount: float, 
        net_amount: float
    ):
        """إشعار المستقبل باستلام الهدية"""
        try:
            # سيتم تنفيذ هذا في الجزء الخاص بالإشعارات
            pass
        except Exception as e:
            logger.error(f"خطأ في notify_gift_received: {e}")

# نسخة عاملة للاستخدام السريع
payment_processor = PaymentProcessor()