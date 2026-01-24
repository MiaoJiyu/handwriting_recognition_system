from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class TrainingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(TrainingJobStatus), nullable=False, default=TrainingJobStatus.PENDING, index=True)
    progress = Column(Float, default=0.0)  # 0.0 - 1.0
    model_version_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    model = relationship("Model", back_populates="training_jobs")
