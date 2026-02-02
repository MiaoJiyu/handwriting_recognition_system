"""
Scheduled Tasks API

提供定时任务的CRUD操作和执行管理
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, field_serializer
from datetime import datetime, timezone
import croniter

from ..core.database import get_db
from ..models.scheduled_task import (
    ScheduledTask, ScheduledTaskExecution,
    ScheduleStatus, ScheduleTriggerType
)
from ..models.training_job import TrainingJob, TrainingJobStatus
from ..models.user import User
from ..models.school import School
from ..utils.dependencies import require_teacher_or_above, get_current_user, CurrentUserResponse
from ..services.task_scheduler import task_scheduler

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])


class ScheduledTaskResponse(BaseModel):
    """定时任务响应"""
    id: int
    name: str
    description: str | None
    status: str
    trigger_type: str
    interval_seconds: int | None
    cron_expression: str | None
    run_at: datetime | None
    training_mode: str
    school_id: int | None
    school_name: str | None
    force_retrain: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    total_runs: int
    success_runs: int
    failed_runs: int
    last_error: str | None
    created_by: int
    creator_name: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at', 'last_run_at', 'next_run_at', 'run_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求"""
    name: str
    description: str | None = None
    trigger_type: ScheduleTriggerType
    interval_seconds: int | None = None
    cron_expression: str | None = None
    run_at: datetime | None = None
    training_mode: str = "full"  # full or incremental
    school_id: int | None = None
    force_retrain: bool = False

    @field_validator('cron_expression')
    def validate_cron(cls, v, info):
        if info.data.get('trigger_type') == ScheduleTriggerType.CRON:
            if not v:
                raise ValueError('Cron expression is required for cron trigger type')
            # 验证cron表达式格式
            try:
                parts = v.split()
                if len(parts) != 5:
                    raise ValueError('Cron expression must have 5 parts: minute hour day month day_of_week')
                # 验证基本格式
                croniter.croniter(v)
            except Exception as e:
                raise ValueError(f'Invalid cron expression: {e}')
        return v

    @field_validator('run_at')
    def validate_run_at(cls, v, info):
        if info.data.get('trigger_type') == ScheduleTriggerType.ONCE:
            if not v:
                raise ValueError('run_at is required for once trigger type')
            if v.tzinfo is None:
                raise ValueError('run_at must be timezone-aware')
        return v

    @field_validator('interval_seconds')
    def validate_interval(cls, v, info):
        if info.data.get('trigger_type') == ScheduleTriggerType.INTERVAL:
            if not v or v <= 0:
                raise ValueError('interval_seconds must be positive for interval trigger type')
        return v

    @field_validator('training_mode')
    def validate_training_mode(cls, v):
        if v not in ('full', 'incremental'):
            raise ValueError('training_mode must be either "full" or "incremental"')
        return v


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""
    name: str | None = None
    description: str | None = None
    status: ScheduleStatus | None = None
    trigger_type: ScheduleTriggerType | None = None
    interval_seconds: int | None = None
    cron_expression: str | None = None
    run_at: datetime | None = None
    training_mode: str | None = None
    school_id: int | None = None
    force_retrain: bool | None = None


class ScheduledTaskExecutionResponse(BaseModel):
    """定时任务执行记录响应"""
    id: int
    scheduled_task_id: int
    training_job_id: int | None
    started_at: datetime
    completed_at: datetime | None
    status: str
    output: str | None
    error_message: str | None

    class Config:
        from_attributes = True

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


@router.post("", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """创建定时任务"""
    # 检查学校是否存在
    if task_data.school_id:
        school = db.query(School).filter(School.id == task_data.school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"学校 {task_data.school_id} 不存在"
            )

    # 创建任务
    task = ScheduledTask(
        name=task_data.name,
        description=task_data.description,
        status=ScheduleStatus.ACTIVE,
        trigger_type=task_data.trigger_type,
        interval_seconds=task_data.interval_seconds,
        cron_expression=task_data.cron_expression,
        run_at=task_data.run_at,
        training_mode=task_data.training_mode,
        school_id=task_data.school_id,
        force_retrain=task_data.force_retrain,
        created_by=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 调度任务
    success = await task_scheduler.schedule_task(task.id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="调度任务失败"
        )

    return _task_to_response(task, db)


@router.get("", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks(
    status: Optional[ScheduleStatus] = None,
    school_id: Optional[int] = None,
    training_mode: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """列出定时任务"""
    query = db.query(ScheduledTask)

    # 根据用户角色过滤
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id:
            query = query.filter(ScheduledTask.school_id == school_admin.school_id)
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id:
            query = query.filter(ScheduledTask.school_id == teacher.school_id)

    # 应用过滤条件
    if status:
        query = query.filter(ScheduledTask.status == status)
    if school_id:
        query = query.filter(ScheduledTask.school_id == school_id)
    if training_mode:
        query = query.filter(ScheduledTask.training_mode == training_mode)

    tasks = query.order_by(ScheduledTask.created_at.desc()).offset(skip).limit(limit).all()

    return [_task_to_response(task, db) for task in tasks]


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取定时任务详情"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此任务"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此任务"
            )

    return _task_to_response(task, db)


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: int,
    task_data: ScheduledTaskUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """更新定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此任务"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此任务"
            )

    # 检查学校是否存在
    if task_data.school_id is not None:
        school = db.query(School).filter(School.id == task_data.school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"学校 {task_data.school_id} 不存在"
            )

    # 更新字段
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    # 如果状态或触发器配置改变，重新调度任务
    if 'status' in update_data or 'trigger_type' in update_data:
        if task.status == ScheduleStatus.ACTIVE:
            await task_scheduler.schedule_task(task.id, db=db)
        else:
            await task_scheduler.pause_task(task.id, db=db)

    return _task_to_response(task, db)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """删除定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此任务"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此任务"
            )

    # 取消调度
    await task_scheduler.unschedule_task(task_id)

    # 删除任务
    db.delete(task)
    db.commit()

    return None


@router.post("/{task_id}/pause", response_model=ScheduledTaskResponse)
async def pause_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """暂停定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权暂停此任务"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权暂停此任务"
            )

    await task_scheduler.pause_task(task_id, db=db)

    db.refresh(task)
    return _task_to_response(task, db)


@router.post("/{task_id}/resume", response_model=ScheduledTaskResponse)
async def resume_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """恢复定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权恢复此任务"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权恢复此任务"
            )

    success = await task_scheduler.resume_task(task_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复任务失败"
        )

    db.refresh(task)
    return _task_to_response(task, db)


@router.get("/{task_id}/executions", response_model=List[ScheduledTaskExecutionResponse])
async def list_task_executions(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """列出任务的执行记录"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"定时任务 {task_id} 不存在"
        )

    # 权限检查
    if current_user.role == "school_admin":
        school_admin = db.query(User).filter(User.id == current_user.id).first()
        if school_admin and school_admin.school_id and task.school_id != school_admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此任务的执行记录"
            )
    elif current_user.role == "teacher":
        teacher = db.query(User).filter(User.id == current_user.id).first()
        if teacher and teacher.school_id and task.school_id != teacher.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此任务的执行记录"
            )

    executions = db.query(ScheduledTaskExecution).filter(
        ScheduledTaskExecution.scheduled_task_id == task_id
    ).order_by(ScheduledTaskExecution.started_at.desc()).offset(skip).limit(limit).all()

    return [_execution_to_response(execution) for execution in executions]


def _task_to_response(task: ScheduledTask, db: Session) -> ScheduledTaskResponse:
    """将任务对象转换为响应对象"""
    # 获取学校名称
    school_name = None
    if task.school_id:
        school = db.query(School).filter(School.id == task.school_id).first()
        if school:
            school_name = school.name

    # 获取创建者名称
    creator_name = None
    if task.created_by:
        creator = db.query(User).filter(User.id == task.created_by).first()
        if creator:
            creator_name = creator.nickname or creator.username

    return ScheduledTaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        trigger_type=task.trigger_type.value,
        interval_seconds=task.interval_seconds,
        cron_expression=task.cron_expression,
        run_at=task.run_at,
        training_mode=task.training_mode,
        school_id=task.school_id,
        school_name=school_name,
        force_retrain=task.force_retrain,
        last_run_at=task.last_run_at,
        next_run_at=task.next_run_at,
        total_runs=task.total_runs,
        success_runs=task.success_runs,
        failed_runs=task.failed_runs,
        last_error=task.last_error,
        created_by=task.created_by,
        creator_name=creator_name,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


def _execution_to_response(execution: ScheduledTaskExecution) -> ScheduledTaskExecutionResponse:
    """将执行记录对象转换为响应对象"""
    return ScheduledTaskExecutionResponse(
        id=execution.id,
        scheduled_task_id=execution.scheduled_task_id,
        training_job_id=execution.training_job_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status.value,
        output=execution.output,
        error_message=execution.error_message
    )
