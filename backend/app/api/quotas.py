from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..core.database import get_db
from ..models.user import User, UserRole
from ..models.quota import Quota
from ..services.quota_service import QuotaService
from ..utils.dependencies import require_system_admin, require_school_admin_or_above, get_current_user, CurrentUserResponse

router = APIRouter(prefix="/quotas", tags=["配额管理"])


# ==================== Pydantic Models ====================

class QuotaRequest(BaseModel):
    """配额创建/更新请求"""
    quota_type: str  # 'user' 或 'school'
    user_id: Optional[int] = None
    school_id: Optional[int] = None
    minute_limit: int = 0
    hour_limit: int = 0
    day_limit: int = 0
    month_limit: int = 0
    total_limit: int = 0
    description: Optional[str] = None


class QuotaResponse(BaseModel):
    """配额响应"""
    id: int
    quota_type: str
    user_id: Optional[int]
    school_id: Optional[int]
    minute_limit: int
    hour_limit: int
    day_limit: int
    month_limit: int
    total_limit: int
    minute_used: int
    hour_used: int
    day_used: int
    month_used: int
    total_used: int
    minute_reset_at: Optional[datetime]
    hour_reset_at: Optional[datetime]
    day_reset_at: Optional[datetime]
    month_reset_at: Optional[datetime]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class BatchQuotaUpdateRequest(BaseModel):
    """批量配额更新请求"""
    user_ids: Optional[List[int]] = None
    school_ids: Optional[List[int]] = None
    minute_limit: int = 0
    hour_limit: int = 0
    day_limit: int = 0
    month_limit: int = 0
    total_limit: int = 0
    description: Optional[str] = None


class QuotaResetRequest(BaseModel):
    """配额重置请求"""
    reset_type: str = "all"  # 'minute', 'hour', 'day', 'month', 'total', 'all'


class QuotaUsageLogResponse(BaseModel):
    """配额使用日志响应"""
    id: int
    user_id: Optional[int]
    school_id: Optional[int]
    quota_type: str
    quota_id: Optional[int]
    recognition_log_id: Optional[int]
    is_allowed: bool
    deny_reason: Optional[str]
    usage_snapshot: Optional[dict]
    created_at: datetime


# ==================== Helper Functions ====================

def _quota_to_response(quota: Quota) -> QuotaResponse:
    """将Quota对象转换为响应模型"""
    return QuotaResponse(
        id=quota.id,
        quota_type=quota.quota_type,
        user_id=quota.user_id,
        school_id=quota.school_id,
        minute_limit=quota.minute_limit,
        hour_limit=quota.hour_limit,
        day_limit=quota.day_limit,
        month_limit=quota.month_limit,
        total_limit=quota.total_limit,
        minute_used=quota.minute_used,
        hour_used=quota.hour_used,
        day_used=quota.day_used,
        month_used=quota.month_used,
        total_used=quota.total_used,
        minute_reset_at=quota.minute_reset_at,
        hour_reset_at=quota.hour_reset_at,
        day_reset_at=quota.day_reset_at,
        month_reset_at=quota.month_reset_at,
        description=quota.description,
        created_at=quota.created_at,
        updated_at=quota.updated_at
    )


# ==================== API Endpoints ====================

@router.get("", response_model=List[QuotaResponse])
async def list_quotas(
    quota_type: Optional[str] = Query(None, description="配额类型: user 或 school"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    school_id: Optional[int] = Query(None, description="学校ID"),
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """获取配额列表"""
    query = db.query(Quota)

    # 根据用户角色过滤数据
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="学生无权查看配额信息"
        )

    if current_user.role == UserRole.TEACHER:
        # 老师只能查看自己的配额
        query = query.filter(Quota.quota_type == "user", Quota.user_id == current_user.id)

    elif current_user.role == UserRole.SCHOOL_ADMIN:
        # 学校管理员可以查看自己学校所有用户的配额
        if quota_type == "school":
            query = query.filter(Quota.quota_type == "school", Quota.school_id == current_user.school_id)
        elif quota_type == "user":
            # 需要关联users表获取同一学校的用户
            from ..models.user import User
            query = query.join(User, Quota.user_id == User.id).filter(
                Quota.quota_type == "user",
                User.school_id == current_user.school_id
            )
        elif user_id:
            # 验证用户是否属于同一学校
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看该用户的配额"
                )
            query = query.filter(Quota.user_id == user_id)
        elif school_id:
            if school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看该学校的配额"
                )
            query = query.filter(Quota.school_id == school_id)

    # 系统管理员可以查看所有配额
    else:
        if quota_type:
            query = query.filter(Quota.quota_type == quota_type)
        if user_id:
            query = query.filter(Quota.user_id == user_id)
        if school_id:
            query = query.filter(Quota.school_id == school_id)

    quotas = query.all()
    return [_quota_to_response(q) for q in quotas]


@router.get("/{quota_id}", response_model=QuotaResponse)
async def get_quota(
    quota_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """获取单个配额详情"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在"
        )

    # 权限检查
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="学生无权查看配额信息"
        )

    if current_user.role == UserRole.TEACHER:
        if quota.quota_type == "user" and quota.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看该配额"
            )

    elif current_user.role == UserRole.SCHOOL_ADMIN:
        if quota.quota_type == "user":
            user = db.query(User).filter(User.id == quota.user_id).first()
            if not user or user.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看该配额"
                )
        elif quota.quota_type == "school" and quota.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看该配额"
            )

    return _quota_to_response(quota)


@router.post("", response_model=QuotaResponse)
async def create_quota(
    request: QuotaRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """创建配额（仅系统管理员）"""
    # 验证请求
    if request.quota_type == "user" and not request.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户配额必须指定user_id"
        )

    if request.quota_type == "school" and not request.school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学校配额必须指定school_id"
        )

    # 检查是否已存在
    existing = db.query(Quota).filter(
        Quota.quota_type == request.quota_type,
        Quota.user_id == request.user_id,
        Quota.school_id == request.school_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该配额已存在"
        )

    # 创建配额
    quota = Quota(
        quota_type=request.quota_type,
        user_id=request.user_id,
        school_id=request.school_id,
        minute_limit=request.minute_limit,
        hour_limit=request.hour_limit,
        day_limit=request.day_limit,
        month_limit=request.month_limit,
        total_limit=request.total_limit,
        description=request.description
    )

    db.add(quota)
    db.commit()
    db.refresh(quota)

    return _quota_to_response(quota)


@router.put("/{quota_id}", response_model=QuotaResponse)
async def update_quota(
    quota_id: int,
    request: QuotaRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """更新配额"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在"
        )

    # 权限检查
    if current_user.role == UserRole.SYSTEM_ADMIN:
        # 系统管理员可以更新所有配额
        pass
    elif current_user.role == UserRole.SCHOOL_ADMIN:
        # 学校管理员只能更新自己学校的配额
        if quota.quota_type == "user":
            user = db.query(User).filter(User.id == quota.user_id).first()
            if not user or user.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权更新该配额"
                )
        elif quota.quota_type == "school" and quota.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权更新该配额"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权更新配额"
        )

    # 更新配额
    quota.minute_limit = request.minute_limit
    quota.hour_limit = request.hour_limit
    quota.day_limit = request.day_limit
    quota.month_limit = request.month_limit
    quota.total_limit = request.total_limit
    quota.description = request.description
    quota.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(quota)

    return _quota_to_response(quota)


@router.post("/batch-update")
async def batch_update_quotas(
    request: BatchQuotaUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """批量更新配额"""
    updated_count = 0

    if request.user_ids:
        # 批量更新用户配额
        if current_user.role == UserRole.SYSTEM_ADMIN:
            updated_count += QuotaService.batch_update_user_quotas(
                db=db,
                user_ids=request.user_ids,
                minute_limit=request.minute_limit,
                hour_limit=request.hour_limit,
                day_limit=request.day_limit,
                month_limit=request.month_limit,
                total_limit=request.total_limit,
                description=request.description
            )
        elif current_user.role == UserRole.SCHOOL_ADMIN:
            # 学校管理员只能更新自己学校的用户配额
            valid_user_ids = [
                user.id for user in db.query(User.id).filter(
                    User.id.in_(request.user_ids),
                    User.school_id == current_user.school_id
                ).all()
            ]

            if valid_user_ids:
                updated_count += QuotaService.batch_update_user_quotas(
                    db=db,
                    user_ids=valid_user_ids,
                    minute_limit=request.minute_limit,
                    hour_limit=request.hour_limit,
                    day_limit=request.day_limit,
                    month_limit=request.month_limit,
                    total_limit=request.total_limit,
                    description=request.description
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权批量更新配额"
            )

    if request.school_ids:
        # 批量更新学校配额（仅系统管理员）
        if current_user.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有系统管理员可以更新学校配额"
            )

        updated_count += QuotaService.batch_update_school_quotas(
            db=db,
            school_ids=request.school_ids,
            minute_limit=request.minute_limit,
            hour_limit=request.hour_limit,
            day_limit=request.day_limit,
            month_limit=request.month_limit,
            total_limit=request.total_limit,
            description=request.description
        )

    return {"updated_count": updated_count}


@router.post("/{quota_id}/reset", response_model=QuotaResponse)
async def reset_quota(
    quota_id: int,
    request: QuotaResetRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """重置配额使用次数"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在"
        )

    # 权限检查
    if current_user.role == UserRole.SYSTEM_ADMIN:
        pass
    elif current_user.role == UserRole.SCHOOL_ADMIN:
        if quota.quota_type == "user":
            user = db.query(User).filter(User.id == quota.user_id).first()
            if not user or user.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权重置该配额"
                )
        elif quota.quota_type == "school" and quota.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权重置该配额"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权重置配额"
        )

    # 重置配额
    quota = QuotaService.reset_quota_usage(
        db=db,
        quota_id=quota_id,
        reset_type=request.reset_type
    )

    return _quota_to_response(quota)


@router.delete("/{quota_id}")
async def delete_quota(
    quota_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """删除配额（仅系统管理员）"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在"
        )

    db.delete(quota)
    db.commit()

    return {"message": "配额已删除"}


@router.get("/{quota_id}/logs", response_model=List[QuotaUsageLogResponse])
async def get_quota_logs(
    quota_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """获取配额使用日志"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在"
        )

    # 权限检查
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="学生无权查看配额日志"
        )

    if current_user.role == UserRole.TEACHER:
        if quota.quota_type == "user" and quota.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看该配额日志"
            )

    elif current_user.role == UserRole.SCHOOL_ADMIN:
        if quota.quota_type == "user":
            user = db.query(User).filter(User.id == quota.user_id).first()
            if not user or user.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看该配额日志"
                )
        elif quota.quota_type == "school" and quota.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看该配额日志"
            )

    # 获取日志
    logs = QuotaService.get_quota_usage_logs(
        db=db,
        user_id=quota.user_id if quota.quota_type == "user" else None,
        school_id=quota.school_id if quota.quota_type == "school" else None,
        limit=limit
    )

    return [QuotaUsageLogResponse(**log) for log in logs]
