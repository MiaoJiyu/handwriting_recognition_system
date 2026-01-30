import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..utils.dependencies import get_current_user, require_system_admin
from ..core.config import Settings
from importlib import reload


class ReloadResponse(BaseModel):
    """重载响应"""
    message: str
    reloaded: bool


router = APIRouter(prefix="/api/system", tags=["系统管理"])


@router.post("/reload", response_model=ReloadResponse)
async def reload_system(
    current_user: User = Depends(require_system_admin)
):
    """
    重载系统配置

    需要系统管理员权限。

    注意：此操作会重新加载配置文件，但不会重启服务。
    对于生产环境，建议使用进程管理器（如systemd、supervisord）来管理服务。
    """
    try:
        # 重新导入配置模块
        import importlib
        import sys

        # 重新加载config模块
        if 'app.core.config' in sys.modules:
            config_module = sys.modules['app.core.config']
            reload(config_module)

            # 更新全局settings实例
            new_settings = Settings()
            settings.__dict__.update(new_settings.__dict__)

        return ReloadResponse(
            message="系统配置已重新加载",
            reloaded=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重载配置失败: {str(e)}"
        )


@router.get("/config", response_model=dict)
async def get_system_config(
    current_user: User = Depends(require_system_admin)
):
    """
    获取当前系统配置（仅系统管理员可访问）

    返回当前加载的配置信息，用于验证配置是否正确加载。
    """
    # 隐藏数据库密码
    if '//' in settings.DATABASE_URL:
        at_index = settings.DATABASE_URL.index('//')
        # 保留到@之前的部分，然后拼接@***来隐藏密码
        database_url = settings.DATABASE_URL[:at_index] + '//***'
    else:
        database_url = settings.DATABASE_URL

    config_dict = {
        "database_url": database_url,
        "inference_service": f"{settings.INFERENCE_SERVICE_HOST}:{settings.INFERENCE_SERVICE_PORT}",
        "redis": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        "upload_dir": settings.UPLOAD_DIR,
        "samples_dir": settings.SAMPLES_DIR,
        "models_dir": settings.MODELS_DIR,
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE // (1024 * 1024),
        "cors_origins": settings.cors_origins_list,
    }
    return config_dict
