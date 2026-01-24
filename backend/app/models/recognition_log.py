from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 识别出的用户ID
    result = Column(JSON, nullable=False)  # Top-K结果，格式: [{"user_id": 1, "score": 0.95}, ...]
    confidence = Column(Float, nullable=False)  # Top-1的置信度
    is_unknown = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 关系
    sample = relationship("Sample", back_populates="recognition_logs")
    user = relationship("User", back_populates="recognition_logs")
