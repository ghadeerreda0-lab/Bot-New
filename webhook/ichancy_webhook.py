"""
Webhook للربط مع منصة Ichancy
"""
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import httpx
from sqlalchemy.orm import Session

from database.models import SessionLocal, User
from config import Config
from utils.security import SecurityUtils

logger = logging.getLogger(__name__)
app = FastAPI(title="Ichancy Webhook API")

class IchancyWebhook:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=Config.ICHANCY_API_URL,
            timeout=30.0
        )
        self.session_cache = {}
    
    async def create_account(
        self, 
        telegram_id: int,
        first_name: str,
        last_name: str = ""
    ) -> Dict[str, Any]:
        """إنشاء حساب على Ichancy"""
        try:
            # محاكاة API حتى يتم ربط API الحقيقي
            # هذا كود مؤقت - سيتم استبداله بالاتصال الحقيقي
            
            import random
            import string
            
            # إنشاء بيانات حساب وهمية
            account_id = ''.join(random.choices(string.digits, k=8))
            username = f"{first_name.lower()}_{random.randint(1000, 9999)}"
            password = SecurityUtils.generate_password()
            
            # في الإصدار الحقيقي، هنا سيتم:
            # 1. تسجيل الدخول إلى لوحة تحكم Ichancy
            # 2. ملء نموذج إنشاء حساب
            # 3. استخراج بيانات الحساب
            
            return {
                "success": True,
                "account_id": account_id,
                "username": username,
                "password": password,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في create_account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deposit_to_account(
        self,
        account_id: str,
        amount: float
    ) -> Dict[str, Any]:
        """شحن رصيد لحساب Ichancy"""
        try:
            # محاكاة API
            # في الإصدار الحقيقي، هنا سيتم:
            # 1. تسجيل الدخول إلى لوحة تحكم Ichancy
            # 2. البحث عن الحساب
            # 3. إضافة الرصيد
            
            logger.info(f"Depositing {amount} to account {account_id}")
            
            # محاكاة التأخير
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "account_id": account_id,
                "amount": amount,
                "new_balance": 0,  # سيتم تحديثه من الاستعلام عن الرصيد
                "transaction_id": f"D{int(datetime.now().timestamp())}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في deposit_to_account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def withdraw_from_account(
        self,
        account_id: str,
        amount: float
    ) -> Dict[str, Any]:
        """سحب رصيد من حساب Ichancy"""
        try:
            # محاكاة API
            logger.info(f"Withdrawing {amount} from account {account_id}")
            
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "account_id": account_id,
                "amount": amount,
                "transaction_id": f"W{int(datetime.now().timestamp())}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في withdraw_from_account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_account_balance(
        self,
        account_id: str
    ) -> Dict[str, Any]:
        """الحصول على رصيد حساب Ichancy"""
        try:
            # محاكاة API
            # في الواقع، هنا سيتم استخراج الرصيد من لوحة التحكم
            
            import random
            
            # محاكاة رصيد عشوائي
            balance = random.uniform(0, 10000)
            
            return {
                "success": True,
                "account_id": account_id,
                "balance": round(balance, 2),
                "currency": "SYP",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في get_account_balance: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_account(
        self,
        account_id: str
    ) -> Dict[str, Any]:
        """حذف حساب Ichancy"""
        try:
            # محاكاة API
            logger.info(f"Deleting account {account_id}")
            
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "account_id": account_id,
                "deleted": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطأ في delete_account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def login_to_panel(self) -> bool:
        """تسجيل الدخول إلى لوحة تحكم Ichancy"""
        try:
            # هذا الكود سيكون مختلفاً تماماً في التنفيذ الحقيقي
            # قد يستخدم selenium أو requests مع session
            
            if Config.ICHANCY_USERNAME and Config.ICHANCY_PASSWORD:
                # محاكاة تسجيل الدخول الناجح
                self.session_cache['logged_in'] = True
                self.session_cache['login_time'] = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في login_to_panel: {e}")
            return False

# إنشاء نسخة من الـ Webhook
ichancy_webhook = IchancyWebhook()

# تبعيات FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# التحقق من التوكن
async def verify_webhook_token(x_token: str = Header(...)):
    if x_token != Config.ICHANCY_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="توكن غير صالح")
    return True

# Routes
@app.post("/api/ichancy/create_account")
async def create_account_endpoint(
    request: Request,
    token_valid: bool = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    """إنشاء حساب جديد على Ichancy"""
    try:
        data = await request.json()
        
        telegram_id = data.get("telegram_id")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="telegram_id مطلوب")
        
        # البحث عن المستخدم
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
        # إنشاء الحساب
        result = await ichancy_webhook.create_account(telegram_id, first_name, last_name)
        
        if result["success"]:
            # تحديث بيانات المستخدم
            user.ichancy_account_id = result["account_id"]
            user.ichancy_username = result["username"]
            db.commit()
            
            return JSONResponse({
                "success": True,
                "message": "تم إنشاء الحساب بنجاح",
                "data": {
                    "account_id": result["account_id"],
                    "username": result["username"],
                    "password": result["password"]
                }
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result["error"]
            }, status_code=500)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في create_account_endpoint: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@app.post("/api/ichancy/deposit")
async def deposit_endpoint(
    request: Request,
    token_valid: bool = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    """شحن رصيد لحساب Ichancy"""
    try:
        data = await request.json()
        
        account_id = data.get("account_id")
        amount = data.get("amount")
        
        if not account_id or not amount:
            raise HTTPException(status_code=400, detail="account_id و amount مطلوبان")
        
        # البحث عن المستخدم
        user = db.query(User).filter(User.ichancy_account_id == account_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        
        # شحن الرصيد
        result = await ichancy_webhook.deposit_to_account(account_id, float(amount))
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "message": "تم الشحن بنجاح",
                "data": {
                    "transaction_id": result["transaction_id"],
                    "amount": result["amount"]
                }
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result["error"]
            }, status_code=500)
            
    except ValueError:
        raise HTTPException(status_code=400, detail="amount يجب أن يكون رقماً")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في deposit_endpoint: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@app.post("/api/ichancy/withdraw")
async def withdraw_endpoint(
    request: Request,
    token_valid: bool = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    """سحب رصيد من حساب Ichancy"""
    try:
        data = await request.json()
        
        account_id = data.get("account_id")
        amount = data.get("amount")
        
        if not account_id or not amount:
            raise HTTPException(status_code=400, detail="account_id و amount مطلوبان")
        
        # البحث عن المستخدم
        user = db.query(User).filter(User.ichancy_account_id == account_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        
        # سحب الرصيد
        result = await ichancy_webhook.withdraw_from_account(account_id, float(amount))
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "message": "تم السحب بنجاح",
                "data": {
                    "transaction_id": result["transaction_id"],
                    "amount": result["amount"]
                }
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result["error"]
            }, status_code=500)
            
    except ValueError:
        raise HTTPException(status_code=400, detail="amount يجب أن يكون رقماً")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في withdraw_endpoint: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@app.get("/api/ichancy/balance/{account_id}")
async def get_balance_endpoint(
    account_id: str,
    token_valid: bool = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    """الحصول على رصيد حساب Ichancy"""
    try:
        # البحث عن المستخدم
        user = db.query(User).filter(User.ichancy_account_id == account_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        
        # الحصول على الرصيد
        result = await ichancy_webhook.get_account_balance(account_id)
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "data": {
                    "account_id": result["account_id"],
                    "balance": result["balance"],
                    "currency": result["currency"]
                }
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result["error"]
            }, status_code=500)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في get_balance_endpoint: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@app.delete("/api/ichancy/account/{account_id}")
async def delete_account_endpoint(
    account_id: str,
    token_valid: bool = Depends(verify_webhook_token),
    db: Session = Depends(get_db)
):
    """حذف حساب Ichancy"""
    try:
        # البحث عن المستخدم
        user = db.query(User).filter(User.ichancy_account_id == account_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        
        # حذف الحساب
        result = await ichancy_webhook.delete_account(account_id)
        
        if result["success"]:
            # تحديث بيانات المستخدم
            user.ichancy_account_id = None
            user.ichancy_username = None
            db.commit()
            
            return JSONResponse({
                "success": True,
                "message": "تم حذف الحساب بنجاح"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result["error"]
            }, status_code=500)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في delete_account_endpoint: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

@app.get("/health")
async def health_check():
    """فحص صحة الخادم"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ichancy-webhook"
    })

@app.post("/api/ichancy/bulk_check_balance")
async def bulk_check_balance(
    request: Request,
    token_valid: bool = Depends(verify_webhook_token)
):
    """فحص أرصدة عدة حسابات دفعة واحدة"""
    try:
        data = await request.json()
        account_ids = data.get("account_ids", [])
        
        if not account_ids or not isinstance(account_ids, list):
            raise HTTPException(status_code=400, detail="account_ids يجب أن يكون مصفوفة")
        
        if len(account_ids) > 100:
            raise HTTPException(status_code=400, detail="الحد الأقصى 100 حساب في المرة")
        
        results = []
        for account_id in account_ids:
            try:
                result = await ichancy_webhook.get_account_balance(account_id)
                results.append({
                    "account_id": account_id,
                    "success": result["success"],
                    "balance": result.get("balance", 0),
                    "error": result.get("error")
                })
                # تأخير بين الطلبات لتجنب الحظر
                await asyncio.sleep(0.5)
            except Exception as e:
                results.append({
                    "account_id": account_id,
                    "success": False,
                    "error": str(e)
                })
        
        return JSONResponse({
            "success": True,
            "results": results,
            "checked_count": len(results)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في bulk_check_balance: {e}")
        raise HTTPException(status_code=500, detail="خطأ داخلي في الخادم")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None
    )