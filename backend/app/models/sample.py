from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class SampleStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class SampleRegion(Base):
    __tablename__ = "sample_regions"

    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False)
    bbox = Column(String(100), nullable=False)  # JSON格式: {"x": 10, "y": 20, "width": 100, "height": 50}
    is_auto_detected = Column(Integer, default=1)  # 1: 自动检测, 0: 手动标注
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sample = relationship("Sample", back_populates="sample_regions")


class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    status = Column(Enum(SampleStatus), nullable=False, default=SampleStatus.PENDING)
    extracted_region_path = Column(String(500), nullable=True)  # 提取的手写区域路径
    sample_metadata = Column(Text, nullable=True)  # JSON格式的元数据（metadata是SQLAlchemy保留字）
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="samples")
    sample_regions = relationship("SampleRegion", back_populates="sample", cascade="all, delete-orphan")
