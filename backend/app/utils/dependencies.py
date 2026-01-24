from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
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
    return user


def require_role(*allowed_roles: UserRole):
    """角色权限装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


def require_system_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求系统管理员权限"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要系统管理员权限"
        )
    return current_user


def require_school_admin_or_above(current_user: User = Depends(get_current_user)) -> User:
    """要求学校管理员或以上权限"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.SCHOOL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要学校管理员或以上权限"
        )
    return current_user


def require_teacher_or_above(current_user: User = Depends(get_current_user)) -> User:
    """要求教师或以上权限"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教师或以上权限"
        )
    return current_user
