from sqlalchemy import Column, Integer, Enum, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class ScheduleStatus(str, enum.Enum):
    """定时任务状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleTriggerType(str, enum.Enum):
    """触发器类型"""
    ONCE = "once"           # 执行一次
    INTERVAL = "interval"   # 间隔执行
    CRON = "cron"           # Cron表达式


class ScheduledTask(Base):
    """定时任务表"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)

    # 任务基本信息
    name = Column(Text, nullable=False, comment="任务名称")
    description = Column(Text, nullable=True, comment="任务描述")
    status = Column(Enum(ScheduleStatus), nullable=False, default=ScheduleStatus.ACTIVE, comment="任务状态")

    # 触发器配置
    trigger_type = Column(Enum(ScheduleTriggerType), nullable=False, comment="触发器类型")

    # 间隔触发器配置
    interval_seconds = Column(Integer, nullable=True, comment="间隔秒数")

    # Cron触发器配置
    cron_expression = Column(Text, nullable=True, comment="Cron表达式")

    # 一次性触发器配置
    run_at = Column(DateTime(timezone=True), nullable=True, comment="执行时间")

    # 任务执行配置
    training_mode = Column(Text, nullable=False, default="full", comment="训练模式: full/incremental")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, comment="学校ID（可选，为空表示全校）")
    force_retrain = Column(Boolean, default=False, comment="是否强制重新训练")

    # 执行统计
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="最后执行时间")
    next_run_at = Column(DateTime(timezone=True), nullable=True, comment="下次执行时间")
    total_runs = Column(Integer, default=0, comment="总执行次数")
    success_runs = Column(Integer, default=0, comment="成功次数")
    failed_runs = Column(Integer, default=0, comment="失败次数")
    last_error = Column(Text, nullable=True, comment="最后一次错误信息")

    # 创建者信息
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    school = relationship("School", back_populates="scheduled_tasks")
    creator = relationship("User", back_populates="scheduled_tasks")
    training_jobs = relationship("TrainingJob", back_populates="scheduled_task", cascade="all, delete-orphan")
    executions = relationship("ScheduledTaskExecution", back_populates="scheduled_task", cascade="all, delete-orphan")


class ScheduledTaskExecution(Base):
    """定时任务执行记录表"""
    __tablename__ = "scheduled_task_executions"

    id = Column(Integer, primary_key=True, index=True)
    scheduled_task_id = Column(Integer, ForeignKey("scheduled_tasks.id"), nullable=False, comment="定时任务ID")
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=True, comment="关联的训练任务ID")

    started_at = Column(DateTime(timezone=True), server_default=func.now(), comment="开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    status = Column(Text, nullable=False, default="running", comment="执行状态")
    output = Column(Text, nullable=True, comment="执行输出")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 关系
    scheduled_task = relationship("ScheduledTask", back_populates="executions")
    training_job = relationship("TrainingJob", back_populates="scheduled_task_execution")

