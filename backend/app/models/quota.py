from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Quota(Base):
    """配额表 - 用于管理用户/学校的识别次数限制"""
    __tablename__ = "quotas"

    id = Column(Integer, primary_key=True, index=True)
    # 配额类型: 'user' 或 'school'
    quota_type = Column(String(20), nullable=False, index=True)

    # 关联的用户ID或学校ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, index=True)

    # 时间窗口限制
    minute_limit = Column(Integer, default=0, nullable=False)  # 每分钟限制，0表示无限制
    hour_limit = Column(Integer, default=0, nullable=False)    # 每小时限制
    day_limit = Column(Integer, default=0, nullable=False)      # 每天限制
    month_limit = Column(Integer, default=0, nullable=False)   # 每月限制
    total_limit = Column(Integer, default=0, nullable=False)   # 总次数限制

    # 使用统计
    minute_used = Column(Integer, default=0, nullable=False)     # 本分钟已用次数
    hour_used = Column(Integer, default=0, nullable=False)       # 本小时已用次数
    day_used = Column(Integer, default=0, nullable=False)       # 本天已用次数
    month_used = Column(Integer, default=0, nullable=False)    # 本月已用次数
    total_used = Column(Integer, default=0, nullable=False)     # 总已用次数

    # 时间窗口重置时间戳
    minute_reset_at = Column(DateTime(timezone=True), nullable=True)
    hour_reset_at = Column(DateTime(timezone=True), nullable=True)
    day_reset_at = Column(DateTime(timezone=True), nullable=True)
    month_reset_at = Column(DateTime(timezone=True), nullable=True)

    # 描述信息
    description = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="quota")
    school = relationship("School", back_populates="quota")

    # 复合索引
    __table_args__ = (
        Index('ix_quota_type_user_id', 'quota_type', 'user_id'),
        Index('ix_quota_type_school_id', 'quota_type', 'school_id'),
    )


class QuotaUsageLog(Base):
    """配额使用日志表 - 记录每次识别请求的配额使用情况"""
    __tablename__ = "quota_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, index=True)

    # 使用的配额信息
    quota_type = Column(String(20), nullable=False)  # 'user' 或 'school'
    quota_id = Column(Integer, nullable=True)

    # 识别结果信息
    recognition_log_id = Column(Integer, ForeignKey("recognition_logs.id"), nullable=True)

    # 是否成功（未超出限制）
    is_allowed = Column(Integer, default=1, nullable=False)  # 1=允许, 0=拒绝

    # 拒绝原因
    deny_reason = Column(String(100), nullable=True)  # 'minute_limit', 'hour_limit', 'day_limit', 'month_limit', 'total_limit'

    # 配额快照（记录当时的配额使用情况）
    usage_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    school = relationship("School")
    recognition_log = relationship("RecognitionLog")

    # 复合索引
    __table_args__ = (
        Index('ix_quota_usage_user_created', 'user_id', 'created_at'),
        Index('ix_quota_usage_school_created', 'school_id', 'created_at'),
    )
