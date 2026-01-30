from fastapi import APIRouter
from pydantic import BaseModel
from ..core.config import settings

router = APIRouter(prefix="/api/config", tags=["配置"])


class ConfigResponse(BaseModel):
    """Configuration response"""
    max_upload_size: int
    max_upload_size_mb: int


@router.get("", response_model=ConfigResponse)
async def get_config():
    """获取系统配置"""
    return ConfigResponse(
        max_upload_size=settings.MAX_UPLOAD_SIZE,
        max_upload_size_mb=settings.MAX_UPLOAD_SIZE // (1024 * 1024)
    )
