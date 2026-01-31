from typing import Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User, UserRole
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


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


async def _get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """内部函数：获取当前用户（返回原始 User 对象）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> CurrentUserResponse:
    """获取当前用户（包含切换状态）"""
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
        created_at=user.created_at.isoformat() if user.created_at else None,
        is_switched=is_switched,
        original_user_id=original_user_id
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
