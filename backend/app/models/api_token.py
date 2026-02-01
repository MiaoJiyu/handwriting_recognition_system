"""
API Token Model for external application integration
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import timezone
from ..core.database import Base


class ApiToken(Base):
    """API Token model for external application integration"""
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)  # Hashed token
    name = Column(String(100), nullable=False)  # Token name/description
    app_name = Column(String(100), nullable=True)  # Application name
    app_version = Column(String(50), nullable=True)  # Application version
    scope = Column(String(50), nullable=False, default="read")  # read, write, admin

    # Permissions - specific API endpoints that can be accessed
    can_read_samples = Column(Boolean, default=True)
    can_write_samples = Column(Boolean, default=False)
    can_recognize = Column(Boolean, default=False)
    can_read_users = Column(Boolean, default=True)
    can_manage_users = Column(Boolean, default=False)
    can_manage_schools = Column(Boolean, default=False)
    can_manage_training = Column(Boolean, default=False)

    # Owner information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)  # For multi-tenant

    # Status
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_ip = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_tokens")

    def __repr__(self):
        return f"<ApiToken(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    def _ensure_utc(self, dt):
        """Ensure datetime is timezone-aware (UTC)"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume naive datetime is in UTC
            return dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if it has a different timezone
        return dt.astimezone(timezone.utc)

    def to_dict(self, include_token=False):
        """Convert to dictionary, optionally including token"""
        # Ensure all datetime fields are timezone-aware (UTC)
        created_at = self._ensure_utc(self.created_at)
        expires_at = self._ensure_utc(self.expires_at)
        last_used_at = self._ensure_utc(self.last_used_at)
        revoked_at = self._ensure_utc(self.revoked_at)

        data = {
            "id": self.id,
            "name": self.name,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "scope": self.scope,
            "can_read_samples": self.can_read_samples,
            "can_write_samples": self.can_write_samples,
            "can_recognize": self.can_recognize,
            "can_read_users": self.can_read_users,
            "can_manage_users": self.can_manage_users,
            "can_manage_schools": self.can_manage_schools,
            "can_manage_training": self.can_manage_training,
            "is_active": self.is_active,
            "is_revoked": self.is_revoked,
            "created_at": created_at.isoformat() if created_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "last_used_at": last_used_at.isoformat() if last_used_at else None,
            "usage_count": self.usage_count
        }

        if include_token:
            data["token"] = self.token

        return data
