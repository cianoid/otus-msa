from .auth import router as auth_router
from .probes import router as main_router

__all__ = [auth_router, main_router]
