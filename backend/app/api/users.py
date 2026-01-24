from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..models.user import User, UserRole
from ..utils.dependencies import (
    require_system_admin,
    require_school_admin_or_above,
    get_current_user
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    school_id: Optional[int] = None


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[UserRole] = None
    school_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    school_id: int | None

    class Config:
        from_attributes = True


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """创建用户"""
    # 检查权限：学校管理员只能创建本校用户
    if current_user.role == UserRole.SCHOOL_ADMIN:
        if user_data.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能创建本校用户"
            )
        # 学校管理员不能创建系统管理员
        if user_data.role == UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权创建系统管理员"
            )
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    from ..utils.security import get_password_hash
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        school_id=user_data.school_id or current_user.school_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("", response_model=List[UserResponse])
async def list_users(
    school_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """列出用户"""
    query = db.query(User)
    
    # 学校管理员只能查看本校用户
    if current_user.role == UserRole.SCHOOL_ADMIN:
        query = query.filter(User.school_id == current_user.school_id)
    elif school_id:
        query = query.filter(User.school_id == school_id)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 权限检查
    if current_user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看其他学校用户"
            )
    elif current_user.role == UserRole.STUDENT:
        if user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能查看自己的信息"
            )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 权限检查
    if current_user.role == UserRole.SCHOOL_ADMIN:
        if user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改其他学校用户"
            )
        # 学校管理员不能修改角色为系统管理员
        if user_data.role == UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权设置系统管理员角色"
            )
    
    if user_data.password:
        from ..utils.security import get_password_hash
        user.password_hash = get_password_hash(user_data.password)
    if user_data.role:
        user.role = user_data.role
    if user_data.school_id is not None:
        user.school_id = user_data.school_id
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """删除用户（仅系统管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db.delete(user)
    db.commit()
    return None
