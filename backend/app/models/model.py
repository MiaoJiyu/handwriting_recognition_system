from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    accuracy = Column(Float, nullable=True)
    training_samples_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)
    model_metadata = Column(Text, nullable=True)  # JSON格式的元数据（metadata是SQLAlchemy保留字）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    training_jobs = relationship("TrainingJob", back_populates="model")
