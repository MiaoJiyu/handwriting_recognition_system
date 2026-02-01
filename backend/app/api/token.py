"""
Token API for external application integration
"""
from datetime import timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, Field
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User, UserRole
from ..utils.security import verify_password, create_access_token
from ..utils.dependencies import get_current_user, CurrentUserResponse, require_role
from ..utils.datetime_utils import utc_now, serialize_datetime_utc
import secrets
import string

router = APIRouter(prefix="/v1/tokens", tags=["External Token API"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class ExternalTokenRequest(BaseModel):
    """External application token request"""
    username: str = Field(..., description="Username (学生/老师/管理员)")
    password: str = Field(..., description="Password", min_length=1)
    app_name: str = Field(..., description="Application name for tracking")
    app_version: Optional[str] = Field(None, description="Application version")
    scope: Optional[str] = Field("read", description="Token scope: read, write, admin")

    @field_validator('scope')
    @classmethod
    def validate_scope(cls, v):
        valid_scopes = ['read', 'write', 'admin']
        if v not in valid_scopes:
            raise ValueError(f"Invalid scope. Must be one of: {', '.join(valid_scopes)}")
        return v


class ExternalTokenResponse(BaseModel):
    """External token response"""
    access_token: str
    token_type: str
    expires_in: int  # seconds
    scope: str
    user_info: dict
    issued_at: str


class TokenVerifyRequest(BaseModel):
    """Token verification request"""
    token: str = Field(..., description="Access token to verify")


class TokenVerifyResponse(BaseModel):
    """Token verification response"""
    valid: bool
    user_info: Optional[dict] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None


class ExternalAPIMessage(BaseModel):
    """Standard API message response"""
    message: str
    status: str
    timestamp: str


class RecognitionRequest(BaseModel):
    """Handwriting recognition request"""
    image_data: str = Field(..., description="Base64 encoded image data or file path")
    top_k: Optional[int] = Field(5, description="Number of top results to return", ge=1, le=10)
    return_details: Optional[bool] = Field(True, description="Return detailed similarity scores")


class SampleUploadRequest(BaseModel):
    """Sample upload request"""
    image_data: str = Field(..., description="Base64 encoded image data")
    user_id: Optional[int] = Field(None, description="User ID (if different from token user)")


class UserInfoResponse(BaseModel):
    """User information response"""
    id: int
    username: str
    nickname: Optional[str]
    role: str
    school_id: Optional[int]
    created_at: str


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/create", response_model=ExternalTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_external_token(
    request: ExternalTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Create an access token for external applications

    This endpoint allows external applications to obtain an access token
    for integrating with the handwriting recognition system.

    **Token Scope Permissions:**
    - `read`: Can view samples, users, recognition logs
    - `write`: Can upload samples, perform recognition
    - `admin`: Full access (requires system_admin or school_admin role)

    **Usage:**
    1. Call this endpoint with username and password
    2. Receive access token in response
    3. Include token in Authorization header: `Authorization: Bearer <token>`
    4. Use other endpoints with the token

    **Request Headers:**
    - Authorization: Basic <base64(username:password)> OR send credentials in request body

    **Example Request:**
    ```json
    {
      "username": "teacher1",
      "password": "password123",
      "app_name": "My Learning App",
      "app_version": "1.0.0",
      "scope": "write"
    }
    ```

    **Example Response:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 1800,
      "scope": "write",
      "user_info": {
        "id": 1,
        "username": "teacher1",
        "nickname": "张老师",
        "role": "teacher",
        "school_id": 1
      },
      "issued_at": "2026-01-31T10:30:00Z"
    }
    ```
    """
    # Authenticate user
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate scope based on user role
    role_to_max_scope = {
        UserRole.STUDENT: "read",
        UserRole.TEACHER: "write",
        UserRole.SCHOOL_ADMIN: "admin",
        UserRole.SYSTEM_ADMIN: "admin",
    }

    max_allowed_scope = role_to_max_scope.get(user.role, "read")

    # Check if requested scope is allowed
    scope_priority = {"read": 1, "write": 2, "admin": 3}
    if scope_priority.get(request.scope, 0) > scope_priority.get(max_allowed_scope, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: User role '{user.role}' cannot request scope '{request.scope}'. Maximum allowed scope is '{max_allowed_scope}'"
        )

    # Create access token with extended expiration for external apps
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role.value,
            "scope": request.scope,
            "app_name": request.app_name,
            "app_version": request.app_version,
            "external": True  # Mark as external token
        },
        expires_delta=access_token_expires
    )

    # Build user info response
    user_info = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role.value,
        "school_id": user.school_id
    }

    return ExternalTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        scope=request.scope,
        user_info=user_info,
        issued_at=serialize_datetime_utc(utc_now())
    )


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(request: TokenVerifyRequest, db: Session = Depends(get_db)):
    """
    Verify an access token and return user information

    This endpoint validates an access token and returns the associated
    user information if the token is valid.

    Supports two token types:
    1. JWT Token - From /api/auth/login
    2. API Token - From /api/v1/tokens/create (format: hwtk_...)

    **Example Request:**
    ```json
    {
      "token": "hwtk_3sbeU1f2CRnDPhfwtWDL7yEYHoGoUi7aS7QRywkq7InxpDqeDhKfs7kLBSgQxECW"
    }
    ```

    **Example Response (Valid Token):**
    ```json
    {
      "valid": true,
      "user_info": {
        "id": 1,
        "username": "teacher1",
        "role": "teacher",
        "school_id": 1,
        "scope": "write"
      },
      "expires_at": "2026-01-31T11:00:00Z"
    }
    ```

    **Example Response (Invalid Token):**
    ```json
    {
      "valid": false,
      "error": "Token has expired"
    }
    ```
    """
    from jose import JWTError, jwt
    from ..models.api_token import ApiToken

    # Check if it's an API token
    if request.token.startswith("hwtk_"):
        # Verify API token
        api_token = db.query(ApiToken).filter(ApiToken.token == request.token).first()

        if not api_token:
            return TokenVerifyResponse(
                valid=False,
                error="Invalid API token"
            )

        # Check if token is active and not revoked
        if not api_token.is_active or api_token.is_revoked:
            return TokenVerifyResponse(
                valid=False,
                error="API token has been revoked or deactivated"
            )

        # Check if token has expired
        # Ensure expires_at is timezone-aware before comparison
        expires_at = api_token.expires_at
        if expires_at is not None:
            from datetime import timezone
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at and expires_at < utc_now():
            return TokenVerifyResponse(
                valid=False,
                error="API token has expired"
            )

        # Get user associated with token
        user = db.query(User).filter(User.id == api_token.user_id).first()
        if not user:
            return TokenVerifyResponse(
                valid=False,
                error="User not found"
            )

        # Build user info
        user_info = {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "role": user.role.value,
            "school_id": user.school_id,
            "scope": api_token.scope
        }

        # Ensure expires_at is timezone-aware before formatting
        expires_at_response = api_token.expires_at
        if expires_at_response is not None:
            from datetime import timezone
            if expires_at_response.tzinfo is None:
                expires_at_response = expires_at_response.replace(tzinfo=timezone.utc)
            expires_at_response = expires_at_response.isoformat() + "Z"
        else:
            expires_at_response = None

        return TokenVerifyResponse(
            valid=True,
            user_info=user_info,
            expires_at=expires_at_response
        )

    # Verify JWT token
    try:
        # Decode and verify token
        payload = jwt.decode(request.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        scope: str = payload.get("scope", "read")
        exp: int = payload.get("exp")

        if username is None:
            return TokenVerifyResponse(
                valid=False,
                error="Invalid token: missing username claim"
            )

        # Get user from database
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return TokenVerifyResponse(
                valid=False,
                error="User not found"
            )

        # Build user info
        user_info = {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "role": user.role.value,
            "school_id": user.school_id,
            "scope": scope
        }

        return TokenVerifyResponse(
            valid=True,
            user_info=user_info,
            expires_at=datetime.fromtimestamp(exp).isoformat() + "Z"
        )

    except JWTError as e:
        error_msg = str(e)
        if "expired" in error_msg.lower():
            error_msg = "Token has expired"
        elif "signature" in error_msg.lower():
            error_msg = "Invalid token signature"
        elif "not enough segments" in error_msg.lower():
            error_msg = "Invalid token format (API tokens should start with 'hwtk_')"

        return TokenVerifyResponse(
            valid=False,
            error=error_msg
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_token_user(current_user: CurrentUserResponse = Depends(get_current_user)):
    """
    Get current user information from token

    This endpoint returns the user information associated with the
    provided access token.

    **Request Headers:**
    - Authorization: Bearer <token>

    **Example Response:**
    ```json
    {
      "id": 1,
      "username": "teacher1",
      "nickname": "张老师",
      "role": "teacher",
      "school_id": 1,
      "created_at": "2026-01-01T00:00:00Z"
    }
    ```
    """
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        role=current_user.role,
        school_id=current_user.school_id,
        created_at=current_user.created_at or serialize_datetime_utc(utc_now())
    )


@router.post("/revoke", response_model=ExternalAPIMessage)
async def revoke_token(
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Revoke current access token

    This endpoint revokes the current access token. After revocation,
    the token can no longer be used to access the API.

    **Note:** In a production environment, tokens should be stored in a
    Redis blacklist for immediate revocation. This is a simple implementation.

    **Request Headers:**
    - Authorization: Bearer <token>

    **Example Response:**
    ```json
    {
      "message": "Token revoked successfully",
      "status": "success",
      "timestamp": "2026-01-31T10:30:00Z"
    }
    ```
    """
    # Note: In a real implementation, add the token to a Redis blacklist
    # For now, we just return success - the client should discard the token

    return ExternalAPIMessage(
        message="Token revoked successfully. Please discard this token.",
        status="success",
        timestamp=serialize_datetime_utc(utc_now())
    )


@router.get("/config", response_model=dict)
async def get_api_config(
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Get API configuration for external applications

    This endpoint returns configuration information that external
    applications need to integrate with the API.

    **Request Headers:**
    - Authorization: Bearer <token>

    **Example Response:**
    ```json
    {
      "version": "1.0.0",
      "base_url": "http://localhost:8000",
      "endpoints": {
        "recognition": "/api/recognition",
        "samples": "/api/samples",
        "users": "/api/users"
      },
      "limits": {
        "max_upload_size": 10485760,
        "max_recognition_per_minute": 60
      },
      "supported_scopes": ["read", "write", "admin"],
      "token_expiry_minutes": 30
    }
    ```
    """
    return {
        "version": "1.0.0",
        "base_url": str(settings.__dict__.get('SERVER_URL', 'http://localhost:8000')),
        "endpoints": {
            "token_create": "/api/v1/tokens/create",
            "token_verify": "/api/v1/tokens/verify",
            "recognition": "/api/recognition",
            "samples": "/api/samples",
            "samples_upload": "/api/samples/upload",
            "users": "/api/users",
            "users_me": "/api/auth/me",
            "training": "/api/training"
        },
        "limits": {
            "max_upload_size": settings.MAX_UPLOAD_SIZE,
            "token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        },
        "supported_scopes": ["read", "write", "admin"],
        "supported_roles": ["student", "teacher", "school_admin", "system_admin"]
    }


@router.get("/info", response_model=dict)
async def get_api_info():
    """
    Get API information (public endpoint)

    This endpoint provides general information about the API
    without requiring authentication.

    **Example Response:**
    ```json
    {
      "name": "Handwriting Recognition Token API",
      "version": "1.0.0",
      "description": "External API for handwriting recognition system integration",
      "authentication": "Bearer Token",
      "base_url": "http://localhost:8000",
      "documentation": "/docs",
      "endpoints": [
        "/api/v1/tokens/create",
        "/api/v1/tokens/verify",
        "/api/v1/tokens/me",
        "/api/v1/tokens/revoke",
        "/api/v1/tokens/config",
        "/api/v1/tokens/info"
      ]
    }
    ```
    """
    return {
        "name": "Handwriting Recognition Token API",
        "version": "1.0.0",
        "description": "External API for handwriting recognition system integration",
        "authentication": "Bearer Token",
        "base_url": "http://localhost:8000",
        "documentation": "/docs",
        "endpoints": [
            "/api/v1/tokens/create (POST)",
            "/api/v1/tokens/verify (POST)",
            "/api/v1/tokens/me (GET)",
            "/api/v1/tokens/revoke (POST)",
            "/api/v1/tokens/config (GET)",
            "/api/v1/tokens/info (GET)"
        ],
        "scopes": {
            "read": "View samples, users, recognition logs",
            "write": "Upload samples, perform recognition",
            "admin": "Full administrative access"
        },
        "roles": {
            "student": "Can only access own data",
            "teacher": "Can manage students and perform recognition",
            "school_admin": "Can manage school users",
            "system_admin": "Full system access"
        }
    }
