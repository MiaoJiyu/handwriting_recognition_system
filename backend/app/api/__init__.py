from .auth import router as auth_router
from .users import router as users_router
from .training import router as training_router
from .recognition import router as recognition_router
from .schools import router as schools_router
from .samples import router as samples_router
from .config import router as config_router
from .system import router as system_router

__all__ = [
    "auth_router",
    "users_router",
    "training_router",
    "recognition_router",
    "schools_router",
    "samples_router",
    "config_router",
    "system_router"
]
