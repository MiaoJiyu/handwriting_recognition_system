from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class SeparationMode(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class SampleStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Sample(Base):
    __tablename__ = "samples"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    annotation_data = Column(JSON, nullable=True)  # 存储手动标注区域坐标
    separation_mode = Column(Enum(SeparationMode), nullable=False, default=SeparationMode.AUTO)
    status = Column(Enum(SampleStatus), nullable=False, default=SampleStatus.PENDING, index=True)
    extracted_region_path = Column(String(500), nullable=True)  # 提取的手写区域路径
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="samples")
    recognition_logs = relationship("RecognitionLog", back_populates="sample")
