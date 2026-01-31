from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class RateLimitConfig(Base):
    """识别次数限制配置"""
    __tablename__ = "rate_limit_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为空表示全局配置
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    # 限制配置
    per_minute = Column(Integer, default=10, nullable=False)  # 每分钟限制
    per_hour = Column(Integer, default=100, nullable=False)   # 每小时限制
    per_day = Column(Integer, default=1000, nullable=False)    # 每天限制
    total_limit = Column(Integer, default=10000, nullable=False)  # 总次数限制
    # 创建和更新时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    school = relationship("School")


class RecognitionUsage(Base):
    """识别使用记录"""
    __tablename__ = "recognition_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)  # 继承自用户
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    success = Column(Integer, default=1)  # 1=成功, 0=失败
    error_message = Column(Text, nullable=True)

    # 关系
    user = relationship("User")
    school = relationship("School")
