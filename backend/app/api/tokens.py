"""
API Token Management Endpoints
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..models.api_token import ApiToken
from ..utils.dependencies import get_current_user, CurrentUserResponse, require_school_admin_or_above
from ..utils.datetime_utils import utc_now, serialize_datetime_utc
import secrets
import string

router = APIRouter(prefix="/tokens", tags=["Token Management"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CreateTokenRequest(BaseModel):
    """Create API Token request"""
    name: str = Field(..., description="Token name/description", min_length=1, max_length=100)
    app_name: Optional[str] = Field(None, description="Application name")
    app_version: Optional[str] = Field(None, description="Application version")
    scope: str = Field("read", description="Token scope: read, write, admin")
    permissions: List[str] = Field(default_factory=list, description="Specific permissions")
    expiration_type: str = Field("30d", description="Expiration type: 1d, 7d, 30d, 90d, never, custom")
    custom_expires_at: Optional[str] = Field(None, description="Custom expiration datetime in ISO format (for expiration_type='custom')")
    confirmed: bool = Field(False, description="User confirmation for tokens >90 days or never-expiring")

    @property
    def permission_map(self):
        """Convert permission list to permission dict"""
        perms = {
            'read_samples': False,
            'write_samples': False,
            'recognize': False,
            'read_users': False,
            'manage_users': False,
            'manage_schools': False,
            'manage_training': False
        }

        for perm in self.permissions:
            if perm in perms:
                perms[perm] = True

        # Apply scope-based default permissions
        if self.scope == 'read':
            perms['read_samples'] = True
            perms['read_users'] = True
        elif self.scope == 'write':
            perms['read_samples'] = True
            perms['write_samples'] = True
            perms['recognize'] = True
            perms['read_users'] = True
        elif self.scope == 'admin':
            for key in perms:
                perms[key] = True

        return perms


class TokenResponse(BaseModel):
    """API Token response (without actual token)"""
    id: int
    name: str
    app_name: Optional[str] = None
    app_version: Optional[str] = None
    scope: str
    permissions: dict
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    usage_count: int


class CreateTokenResponse(BaseModel):
    """Create token response (includes token only once)"""
    id: int
    name: str
    token: str  # Only shown once
    scope: str
    permissions: dict
    created_at: str
    expires_at: Optional[str] = None
    message: str


class TokenListResponse(BaseModel):
    """Token list response"""
    total: int
    tokens: List[TokenResponse]


# ============================================================================
# Helper Functions
# ============================================================================

def generate_token():
    """Generate a random API token"""
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(64))
    return f"hwtk_{token}"  # hwtk = handwriting token key


def validate_scope_for_user(scope: str, user_role: str):
    """Validate if user can create token with given scope"""
    scope_priority = {"read": 1, "write": 2, "admin": 3}
    role_to_max_scope = {
        "student": "read",
        "teacher": "write",
        "school_admin": "admin",
        "system_admin": "admin"
    }

    max_allowed = role_to_max_scope.get(user_role, "read")

    if scope_priority.get(scope, 0) > scope_priority.get(max_allowed, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{user_role}' cannot create tokens with scope '{scope}'. Maximum allowed scope is '{max_allowed}'"
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/create", response_model=CreateTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_api_token(
    request: CreateTokenRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API token

    Creates a new API token for external application integration.
    The token is shown only once and cannot be retrieved later.

    **Permissions:**
    - `read_samples`: Can list and view samples
    - `write_samples`: Can upload samples
    - `recognize`: Can perform handwriting recognition
    - `read_users`: Can view user information
    - `manage_users`: Can create, modify, and delete users
    - `manage_schools`: Can create, modify, and delete schools
    - `manage_training`: Can trigger and manage training

    **Scopes:**
    - `read`: Includes read_samples, read_users
    - `write`: Includes read_samples, write_samples, recognize, read_users
    - `admin`: Includes all permissions (requires admin role)
    """
    # Validate scope based on user role
    validate_scope_for_user(request.scope, current_user.role)

    # Generate unique token
    token_str = generate_token()

    # Check for duplicate
    existing = db.query(ApiToken).filter(ApiToken.token == token_str).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token generation failed, please try again"
        )

    # Create token record
    perms = request.permission_map

    # Calculate expiration based on type
    expires_at = None
    max_days = 90
    days_until_expiry = 0

    if request.expiration_type == "1d":
        expires_at = utc_now() + timedelta(days=1)
        days_until_expiry = 1
    elif request.expiration_type == "7d":
        expires_at = utc_now() + timedelta(days=7)
        days_until_expiry = 7
    elif request.expiration_type == "30d":
        expires_at = utc_now() + timedelta(days=30)
        days_until_expiry = 30
    elif request.expiration_type == "90d":
        expires_at = utc_now() + timedelta(days=90)
        days_until_expiry = 90
    elif request.expiration_type == "never":
        # No expiration - requires confirmation
        if not request.confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Creating a never-expiring token requires confirmation. Please confirm this action."
            )
        expires_at = None
        days_until_expiry = None
    elif request.expiration_type == "custom":
        if not request.custom_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom expiration datetime is required when expiration_type is 'custom'"
            )
        try:
            from ..utils.datetime_utils import parse_datetime_iso
            expires_at = parse_datetime_iso(request.custom_expires_at)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid datetime format. Use ISO format (e.g., 2024-12-31T23:59:59)"
            )
        
        # Check if custom expiration is in the past
        now = utc_now()
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiration date cannot be in the past"
            )
        
        # Calculate days until expiry
        days_until_expiry = (expires_at - now).days
        
        # Check if custom expiration exceeds 90 days and requires confirmation
        if days_until_expiry > max_days and not request.confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Custom expiration exceeds {max_days} days and requires confirmation. Please confirm this action."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid expiration type: {request.expiration_type}. Must be one of: 1d, 7d, 30d, 90d, never, custom"
        )

    api_token = ApiToken(
        token=token_str,
        name=request.name,
        app_name=request.app_name,
        app_version=request.app_version,
        scope=request.scope,
        can_read_samples=perms['read_samples'],
        can_write_samples=perms['write_samples'],
        can_recognize=perms['recognize'],
        can_read_users=perms['read_users'],
        can_manage_users=perms['manage_users'],
        can_manage_schools=perms['manage_schools'],
        can_manage_training=perms['manage_training'],
        user_id=current_user.id,
        school_id=current_user.school_id,
        is_active=True,
        expires_at=expires_at
    )

    db.add(api_token)
    db.commit()
    db.refresh(api_token)

    return CreateTokenResponse(
        id=api_token.id,
        name=api_token.name,
        token=api_token.token,  # Only shown once
        scope=api_token.scope,
        permissions=perms,
        created_at=serialize_datetime_utc(api_token.created_at) or serialize_datetime_utc(utc_now()),
        expires_at=serialize_datetime_utc(api_token.expires_at),
        message="Token created successfully. Save this token now - it will not be shown again!"
    )


@router.get("/list", response_model=TokenListResponse)
async def list_api_tokens(
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API tokens for current user

    Returns a list of all API tokens owned by the current user.
    Note: The actual token value is never returned in this endpoint.
    """
    # Students can only see their own tokens
    # Admins can see all tokens in their school
    query = db.query(ApiToken)

    if current_user.role == "student":
        query = query.filter(ApiToken.user_id == current_user.id)
    elif current_user.role == "school_admin":
        query = query.filter(ApiToken.school_id == current_user.school_id)
    # system_admin can see all tokens

    tokens = query.order_by(ApiToken.created_at.desc()).all()

    total = len(tokens)
    token_responses = []

    for token in tokens:
        token_responses.append(TokenResponse(
            id=token.id,
            name=token.name,
            app_name=token.app_name,
            app_version=token.app_version,
            scope=token.scope,
            permissions={
                'read_samples': token.can_read_samples,
                'write_samples': token.can_write_samples,
                'recognize': token.can_recognize,
                'read_users': token.can_read_users,
                'manage_users': token.can_manage_users,
                'manage_schools': token.can_manage_schools,
                'manage_training': token.can_manage_training
            },
            is_active=token.is_active and not token.is_revoked,
            created_at=serialize_datetime_utc(token.created_at),
            last_used_at=serialize_datetime_utc(token.last_used_at),
            expires_at=serialize_datetime_utc(token.expires_at),
            usage_count=token.usage_count
        ))

    return TokenListResponse(total=total, tokens=token_responses)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_token(
    token_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an API token

    Permanently deletes an API token. Cannot be undone.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Check permission: can only delete own tokens or all tokens if admin
    if current_user.role == "student" and token.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own tokens"
        )

    if current_user.role == "school_admin" and token.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete tokens from your school"
        )

    db.delete(token)
    db.commit()


@router.post("/{token_id}/revoke")
async def revoke_api_token(
    token_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API token

    Revokes (deactivates) a token without deleting it.
    The token can still be viewed but cannot be used.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Check permission
    if current_user.role == "student" and token.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own tokens"
        )

    if current_user.role == "school_admin" and token.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke tokens from your school"
        )

    token.is_revoked = True
    token.revoked_at = utc_now()
    db.commit()

    return {"message": "Token revoked successfully"}


@router.get("/{token_id}", response_model=TokenResponse)
async def get_api_token(
    token_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get API token details

    Returns details about a specific API token.
    The actual token value is never returned.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Check permission
    if current_user.role == "student" and token.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own tokens"
        )

    if current_user.role == "school_admin" and token.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tokens from your school"
        )

    return TokenResponse(
        id=token.id,
        name=token.name,
        app_name=token.app_name,
        app_version=token.app_version,
        scope=token.scope,
        permissions={
            'read_samples': token.can_read_samples,
            'write_samples': token.can_write_samples,
            'recognize': token.can_recognize,
            'read_users': token.can_read_users,
            'manage_users': token.can_manage_users,
            'manage_schools': token.can_manage_schools,
            'manage_training': token.can_manage_training
        },
        is_active=token.is_active and not token.is_revoked,
        created_at=serialize_datetime_utc(token.created_at),
        last_used_at=serialize_datetime_utc(token.last_used_at),
        expires_at=serialize_datetime_utc(token.expires_at),
        usage_count=token.usage_count
    )
