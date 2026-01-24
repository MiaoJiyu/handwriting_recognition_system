from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 识别出的用户ID，可能为None（未知）
    result = Column(Text, nullable=False)  # JSON格式的Top-K结果
    confidence = Column(Float, nullable=False)
    is_unknown = Column(Boolean, default=False)
    image_path = Column(String(500), nullable=True)  # 识别的图片路径
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="recognition_logs")
