from .auth import router as auth_router
from .main import router as main_router
from .user import router as user_router

__all__ = [auth_router, main_router, user_router]
