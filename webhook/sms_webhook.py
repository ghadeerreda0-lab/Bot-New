"""
Webhook لاستقبال ومعالجة رسائل SMS
"""
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database.models import SessionLocal, Transaction, SyriatelCode
from config import Config
from utils.payments import payment_processor

logger = logging.getLogger(__name__)
app = FastAPI(title="SMS Webhook API")

class SMSProcessor:
    def __init__(self):
        self.syriatel_patterns = [
            r"تم تحويل (\d+(?:\.\d+)?) ل\.س الى رقم (\d+) برقم عملية (\d+)",
            r"تحويل مبلغ (\d+(?:\.\d+)?) ل\.س الى (\d+) رقم العمليه (\d+)",
            r"تحويل (\d+(?:\.\d+)?) ل\.س لرقم (\d+) عملية (\d+)",
        ]
        
        self.cham_patterns = [
            r"تم استلام (\d+(?:\.\d+)?) ل\.س من (\d+) رقم العمليه (\w+)",
            r"تحويل (\d+(?:\.\d+)?) ل\.س من (\d+) رقم (\w+)",
        ]
    
    def parse_syriatel_sms(self, text: str) -> Optional[Dict[str, Any]]:
        """تحليل رسالة سيرياتيل كاش"""
        text = text.replace(",", "")
        
        for pattern in self.syriatel_patterns:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                phone_number = match.group(2)
                transaction_code = match.group(3)
                
                return {
                    "provider": "syriatel_cash",
                    "amount": amount,
                    "phone_number": phone_number,
                    "transaction_code": transaction_code,
                    "parsed": True
                }
        
        return None
    
    def parse_cham_sms(self, text: str) -> Optional[Dict[str, Any]]:
        """تحليل رسالة شام كاش"""
        text = text.replace(",", "")
        
        for pattern in self.cham_patterns:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                phone_number = match.group(2)
                transaction_code = match.group(3)
                
                return {
                    "provider": "cham_cash",
                    "amount": amount,
                    "phone_number": phone_number,
                    "transaction_code": transaction_code,
                    "parsed": True
                }
        
        return None
    
    async def process_sms(
        self, 
        provider: str,
        sender: str,
        text: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """معالجة رسالة SMS"""
        try:
            parsed_data = None
            
            if provider.lower() == "syriatel":
                parsed_data = self.parse_syriatel_sms(text)
            elif provider.lower() == "cham":
                parsed_data = self.parse_cham_sms(text)
            
            if not parsed_data or not parsed_data.get("parsed"):
                return {
                    "success": False,
                    "error": "تعذر تحليل الرسالة",
                    "processed": False
                }
            
            # البحث عن معاملة تطابق رقم العملية
            db = SessionLocal()
            try:
                transaction = db.query(Transaction).filter(
                    Transaction.transaction_code == parsed_data["transaction_code"],
                    Transaction.payment_method == parsed_data["provider"],
                    Transaction.status == "pending"
                ).first()
                
                if transaction:
                    # تحديث المعاملة
                    transaction.status = "completed"
                    transaction.auto_verified = True
                    transaction.completed_at = timestamp
                    
                    # إذا كان سيرياتيل، تحديث الكود
                    if parsed_data["provider"] == "syriatel_cash":
                        syriatel_code = db.query(SyriatelCode).filter(
                            SyriatelCode.code == sender
                        ).first()
                        
                        if syriatel_code:
                            syriatel_code.current_balance += parsed_data["amount"]
                            if syriatel_code.current_balance >= syriatel_code.max_balance:
                                syriatel_code.is_active = False
                    
                    db.commit()
                    
                    # إشعار المستخدم
                    await self.notify_user_transaction(transaction)
                    
                    return {
                        "success": True,
                        "processed": True,
                        "transaction_id": transaction.id,
                        "amount": parsed_data["amount"],
                        "user_id": transaction.user_id
                    }
                else:
                    # تسجيل SMS غير متطابق للفحص لاحقاً
                    logger.info(f"SMS غير متطابق: {parsed_data}")
                    
                    return {
                        "success": True,
                        "processed": False,
                        "reason": "لا توجد معاملة تطابق رقم العملية",
                        "data": parsed_data
                    }
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"خطأ في process_sms: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed": False
            }
    
    async def notify_user_transaction(self, transaction):
        """إشعار المستخدم بإكمال المعاملة"""
        # سيتم تنفيذ هذا في وحدة الإشعارات
        pass
    
    async def bulk_process_sms(self, sms_list: List[Dict]) -> Dict[str, Any]:
        """معالجة عدة رسائل SMS دفعة واحدة"""
        results = []
        
        for sms in sms_list:
            result = await self.process_sms(
                provider=sms.get("provider"),
                sender=sms.get("sender"),
                text=sms.get("text"),
                timestamp=sms.get("timestamp", datetime.utcnow())
            )
            results.append(result)
            
            # تأخير لتجنب الحمل الزائد
            await asyncio.sleep(0.1)
        
        successful = sum(1 for r in results if r["success"])
        processed = sum(1 for r in results if r.get("processed"))
        
        return {
            "total": len(results),
            "successful": successful,
            "processed": processed,
            "results": results
        }

# إنشاء المعالج
sms_processor = SMSProcessor()

# Routes
@app.post("/api/sms/receive")
async def receive_sms(
    request: Request,
    background_tasks: BackgroundTasks
):
    """استقبال رسالة SMS جديدة"""
    try:
        data = await request.json()
        
        provider = data.get("provider")
        sender = data.get("sender")
        text = data.get("text")
        timestamp_str = data.get("timestamp")
        
        if not all([provider, sender, text]):
            raise HTTPException(status_code=400, detail="بيانات غير مكتملة")
        
        # تحويل التاريخ
        try:
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
        except:
            timestamp = datetime.utcnow()
        
        # معالجة في الخلفية
        background_tasks.add_task(
            sms_processor.process_sms,
            provider, sender, text, timestamp
        )
        
        return {
            "success": True,
            "message": "تم استلام الرسالة وسيتم معالجتها",
            "provider": provider,
            "sender": sender[:3] + "****" + sender[-3:] if len(sender) > 6 else "****"
        }
        
    except Exception as e:
        logger.error(f"خطأ في receive_sms: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي")

@app.post("/api/sms/bulk_receive")
async def bulk_receive_sms(
    request: Request,
    background_tasks: BackgroundTasks
):
    """استقبال عدة رسائل SMS دفعة واحدة"""
    try:
        data = await request.json()
        sms_list = data.get("messages", [])
        
        if not isinstance(sms_list, list) or len(sms_list) > 100:
            raise HTTPException(
                status_code=400, 
                detail="يجب أن تكون messages مصفوفة وبحد أقصى 100 رسالة"
            )
        
        # التحقق من البيانات
        for sms in sms_list:
            if not all(key in sms for key in ["provider", "sender", "text"]):
                raise HTTPException(status_code=400, detail="بيانات غير مكتملة في إحدى الرسائل")
        
        # معالجة في الخلفية
        background_tasks.add_task(
            sms_processor.bulk_process_sms,
            sms_list
        )
        
        return {
            "success": True,
            "message": f"تم استلام {len(sms_list)} رسالة وسيتم معالجتها",
            "count": len(sms_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في bulk_receive_sms: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي")

@app.get("/api/sms/test_parse")
async def test_parse_sms(
    provider: str,
    text: str
):
    """اختبار تحليل رسالة SMS"""
    try:
        result = None
        
        if provider.lower() == "syriatel":
            result = sms_processor.parse_syriatel_sms(text)
        elif provider.lower() == "cham":
            result = sms_processor.parse_cham_sms(text)
        else:
            raise HTTPException(status_code=400, detail="provider غير معروف")
        
        return {
            "success": True,
            "parsed": result is not None,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"خطأ في test_parse_sms: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي")

@app.post("/api/sms/manual_verify")
async def manual_verify_transaction(
    request: Request,
    db: Session = Depends(lambda: SessionLocal())
):
    """التحقق اليدوي من معاملة"""
    try:
        data = await request.json()
        
        transaction_code = data.get("transaction_code")
        provider = data.get("provider")
        
        if not transaction_code or not provider:
            raise HTTPException(status_code=400, detail="transaction_code و provider مطلوبان")
        
        # البحث عن المعاملة
        transaction = db.query(Transaction).filter(
            Transaction.transaction_code == transaction_code,
            Transaction.payment_method == provider,
            Transaction.status == "pending"
        ).first()
        
        if not transaction:
            return {
                "success": False,
                "error": "لم يتم العثور على معاملة تطابق البيانات"
            }
        
        # تحديث المعاملة
        transaction.status = "completed"
        transaction.auto_verified = False  # لأنها يدوية
        transaction.completed_at = datetime.utcnow()
        
        # تحديث رصيد المستخدم
        user = transaction.user
        user.balance += transaction.net_amount
        
        db.commit()
        
        return {
            "success": True,
            "message": "تم التحقق من المعاملة بنجاح",
            "transaction_id": transaction.id,
            "user_id": user.id,
            "amount": transaction.net_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطأ في manual_verify_transaction: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي")
    finally:
        db.close()

@app.get("/api/sms/pending_transactions")
async def get_pending_transactions(
    provider: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(lambda: SessionLocal())
):
    """الحصول على المعاملات المعلقة"""
    try:
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.query(Transaction).filter(
            Transaction.status == "pending",
            Transaction.created_at >= cutoff_time
        )
        
        if provider:
            query = query.filter(Transaction.payment_method == provider)
        
        transactions = query.order_by(Transaction.created_at.desc()).limit(100).all()
        
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount,
                "payment_method": t.payment_method,
                "transaction_code": t.transaction_code,
                "created_at": t.created_at.isoformat(),
                "user_telegram_id": t.user.telegram_id,
                "username": t.user.username
            })
        
        return {
            "success": True,
            "count": len(result),
            "transactions": result
        }
        
    except Exception as e:
        logger.error(f"خطأ في get_pending_transactions: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي")
    finally:
        db.close()

@app.get("/health")
async def health_check():
    """فحص صحة الخادم"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "sms-webhook"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_config=None
    )