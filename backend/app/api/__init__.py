from .auth import router as auth_router
from .users import router as users_router
from .training import router as training_router
from .recognition import router as recognition_router
from .schools import router as schools_router
from .samples import router as samples_router
from .config import router as config_router
from .system import router as system_router
from .token import router as token_router, token_management_router as tokens_management_router
from .scheduled_tasks import router as scheduled_tasks_router
from .quotas import router as quotas_router
from .monitoring import router as monitoring_router

__all__ = [
    "auth_router",
    "users_router",
    "training_router",
    "recognition_router",
    "schools_router",
    "samples_router",
    "config_router",
    "system_router",
    "token_router",
    "tokens_management_router",
    "scheduled_tasks_router",
    "quotas_router",
    "monitoring_router"
]
