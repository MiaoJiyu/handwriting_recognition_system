from typing import Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User, UserRole
from ..models.api_token import ApiToken
from .datetime_utils import utc_now, serialize_datetime
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


class CurrentUserResponse(BaseModel):
    """当前用户响应（包含切换状态）"""
    id: int
    username: str
    nickname: Optional[str] = None
    role: str
    school_id: Optional[int] = None
    created_at: Optional[str] = None
    is_switched: bool = False
    original_user_id: Optional[int] = None
    token_type: Optional[str] = None  # 'jwt' or 'api_token'


async def _get_auth_token(
    authorization: Optional[str] = None,
) -> str:
    """Extract token from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if authorization.startswith("Bearer "):
        return authorization[7:]  # Remove "Bearer " prefix
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，应使用 Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_api_token(token: str, db: Session) -> Optional[User]:
    """Verify API token and return associated user"""
    if not token.startswith("hwtk_"):
        return None

    # Query the token from database
    api_token = db.query(ApiToken).filter(ApiToken.token == token).first()

    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is active and not revoked
    if not api_token.is_active or api_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Token已被撤销或失效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token has expired
    if api_token.expires_at and api_token.expires_at < utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Token已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the user associated with the token
    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used timestamp and usage count
    api_token.last_used_at = utc_now()
    api_token.usage_count += 1
    db.commit()

    return user


async def _get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """内部函数：获取当前用户（返回原始 User 对象）

    支持两种token类型：
    1. JWT Token（从 /api/auth/login 获取）
    2. API Token（从 /api/v1/tokens/create 获取，格式：hwtk_...）
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to verify as API token first (hwtk_ prefix)
    if token and token.startswith("hwtk_"):
        try:
            return _verify_api_token(token, db)
        except HTTPException as e:
            if "无效" in e.detail or "已撤销" in e.detail or "已过期" in e.detail:
                raise e
            # If it's a database error, fall through to JWT verification

    # Try to verify as JWT token
    try:
        if not token:
            raise credentials_exception

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        # If JWT verification fails and token doesn't start with hwtk_, return error
        if not token or not token.startswith("hwtk_"):
            raise credentials_exception
        # If it starts with hwtk_ but failed earlier, re-raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    # 如果用户已切换到其他用户，返回切换后的用户
    if user.switched_user_id:
        switched_user = db.query(User).filter(User.id == user.switched_user_id).first()
        if switched_user:
            return switched_user

    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> CurrentUserResponse:
    """获取当前用户（包含切换状态）

    支持两种token类型：
    1. JWT Token（从 /api/auth/login 获取）
    2. API Token（从 /api/v1/tokens/create 获取，格式：hwtk_...）
    """
    # Determine token type
    token_type = 'jwt'
    if token and token.startswith('hwtk_'):
        token_type = 'api_token'

    user = await _get_current_user(token, db)

    # 检查是否为切换后的用户
    original_user_id = None
    is_switched = False

    # 如果当前用户有 switched_user_id，说明是原始admin用户
    # 需要查找哪个用户切换到了当前用户
    admin_user = db.query(User).filter(User.switched_user_id == user.id).first()
    if admin_user:
        is_switched = True
        original_user_id = admin_user.id

    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        school_id=user.school_id,
        created_at=serialize_datetime(user.created_at),
        is_switched=is_switched,
        original_user_id=original_user_id,
        token_type=token_type
    )


def require_role(*allowed_roles: UserRole):
    """角色权限装饰器"""
    def role_checker(current_user: CurrentUserResponse = Depends(get_current_user)) -> CurrentUserResponse:
        # Convert string role to UserRole for comparison
        role_str = current_user.role
        if isinstance(current_user.role, str):
            # Convert string to UserRole
            user_role = UserRole(current_user.role)
        else:
            user_role = current_user.role
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


def require_system_admin(current_user: CurrentUserResponse = Depends(get_current_user)) -> CurrentUserResponse:
    """要求系统管理员权限"""
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要系统管理员权限"
        )
    return current_user


def require_school_admin_or_above(current_user: CurrentUserResponse = Depends(get_current_user)) -> CurrentUserResponse:
    """要求学校管理员或以上权限"""
    if current_user.role not in ["system_admin", "school_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要学校管理员或以上权限"
        )
    return current_user


def require_teacher_or_above(current_user: CurrentUserResponse = Depends(get_current_user)) -> CurrentUserResponse:
    """要求教师或以上权限"""
    if current_user.role not in ["system_admin", "school_admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教师或以上权限"
        )
    return current_user
