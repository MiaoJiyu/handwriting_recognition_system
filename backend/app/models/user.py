from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), nullable=True)  # 昵称/学生姓名
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # 系统管理员切换功能
    switched_user_id = Column(Integer, nullable=True)
    switched_to_username = Column(String(50), nullable=True)
    switched_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    school = relationship("School", back_populates="users")
    samples = relationship("Sample", back_populates="user", cascade="all, delete-orphan")
    recognition_logs = relationship("RecognitionLog", back_populates="user")
    user_features = relationship("UserFeature", back_populates="user", cascade="all, delete-orphan")
    api_tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="creator", cascade="all, delete-orphan")
