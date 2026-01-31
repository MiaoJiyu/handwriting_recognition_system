from sqlalchemy import Column, Integer, String, DateTime, Enum as Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class AuditActionType(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    SWITCH_USER = "switch_user"
    CANCEL_SWITCH = "cancel_switch"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(Enum(AuditActionType), nullable=False, default=AuditActionType.LOGIN)
    details = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    actor = relationship("User", foreign_keys=[AuditLog.actor_id], back_populates="actor_logs")
    target_user = relationship("User", foreign_keys=[AuditLog.target_user_id], back_populates="target_user_logs")
