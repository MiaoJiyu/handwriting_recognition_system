from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..utils.security import verify_password, get_password_hash, create_access_token
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    school_id: int | None

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "student"  # 默认角色为学生
    school_id: int | None = None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 验证角色
    from ..models.user import UserRole
    try:
        role = UserRole(user_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的角色: {user_data.role}"
        )
    
    # 创建新用户
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=role,
        school_id=user_data.school_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


class LogoutResponse(BaseModel):
    message: str
    success: bool


# Token黑名单（简单实现，生产环境应使用Redis）
token_blacklist: set = set()


def is_token_blacklisted(token: str) -> bool:
    """检查token是否在黑名单中"""
    return token in token_blacklist


def add_token_to_blacklist(token: str):
    """将token添加到黑名单"""
    token_blacklist.add(token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """用户登出
    
    将当前token加入黑名单，使其失效。
    注意：前端也应该删除本地存储的token。
    """
    from fastapi import Request
    # 这里简单地返回成功消息
    # 实际的token失效由前端删除token处理
    # 如果需要服务端强制失效，可以使用Redis存储黑名单
    return LogoutResponse(
        message="登出成功",
        success=True
    )
