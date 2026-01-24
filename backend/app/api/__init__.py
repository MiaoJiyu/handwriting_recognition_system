from .auth import router as auth_router
from .users import router as users_router
from .training import router as training_router
from .recognition import router as recognition_router
from .schools import router as schools_router

__all__ = [
    "auth_router",
    "users_router",
    "training_router",
    "recognition_router",
    "schools_router"
]
