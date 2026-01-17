"""
نماذج قاعدة البيانات
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    balance = Column(Float, default=0.0)
    ichancy_account_id = Column(String(100), nullable=True)
    ichancy_username = Column(String(100), nullable=True)
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    transactions = relationship("Transaction", back_populates="user")
    referrals = relationship("Referral", foreign_keys="Referral.referred_user_id")
    sent_gifts = relationship("GiftTransaction", foreign_keys="GiftTransaction.sender_id")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # deposit, withdraw, gift, bonus
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=True)
    transaction_code = Column(String(100), nullable=True)  # رقم عملية سيرياتيل/شام
    status = Column(String(20), default="pending")  # pending, completed, rejected, canceled
    admin_id = Column(Integer, nullable=True)  # إذا تمت يدوياً
    auto_verified = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # العلاقات
    user = relationship("User", back_populates="transactions")

class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    is_active = Column(Boolean, default=False)
    total_burned = Column(Float, default=0.0)
    bonus_paid = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # العلاقات
    referrer = relationship("User", foreign_keys=[referrer_id])
    referred_user = relationship("User", foreign_keys=[referred_user_id])

class GiftCode(Base):
    __tablename__ = "gift_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # deposit, withdraw, both
    is_active = Column(Boolean, default=True)
    min_amount = Column(Float, default=0.0)
    max_amount = Column(Float, default=1000000.0)
    fee_percentage = Column(Float, default=0.0)
    fee_fixed = Column(Float, default=0.0)
    settings = Column(JSON, nullable=True)  # إعدادات خاصة بالطريقة
    created_at = Column(DateTime, default=datetime.utcnow)

class SyriatelCode(Base):
    __tablename__ = "syriatel_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    current_balance = Column(Float, default=0.0)
    max_balance = Column(Float, default=5400.0)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Bonus(Base):
    __tablename__ = "bonuses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    bonus_type = Column(String(20), nullable=False)  # normal, conditional
    percentage = Column(Float, default=0.0)
    min_amount = Column(Float, default=0.0)
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False)
    action_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_level = Column(String(20), nullable=False)
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GiftTransaction(Base):
    __tablename__ = "gift_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # العلاقات
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

# إنشاء الجداول
def create_tables():
    Base.metadata.create_all(bind=engine)

# جلسة قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()