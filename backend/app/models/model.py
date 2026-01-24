from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False, index=True)
    model_path = Column(String(500), nullable=False)
    accuracy = Column(Float, nullable=True)
    training_samples_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    training_jobs = relationship("TrainingJob", back_populates="model")
