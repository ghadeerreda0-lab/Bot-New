"""
حزمة معالجات البوت
"""

from .user_handlers import *
from .admin_handlers import *
from .payment_handlers import *
from .callback_handlers import *

__all__ = [
    'register_all_handlers',
    'user_handlers',
    'admin_handlers',
    'payment_handlers',
    'callback_handlers'
]