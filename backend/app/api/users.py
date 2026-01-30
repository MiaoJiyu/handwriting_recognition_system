from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_serializer
from datetime import datetime
import random
import string
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
    nickname: Optional[str] = None  # 昵称/学生姓名
    role: UserRole
    school_id: Optional[int] = None


class UserUpdate(BaseModel):
    password: Optional[str] = None
    nickname: Optional[str] = None  # 昵称/学生姓名
    role: Optional[UserRole] = None
    school_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None  # 昵称/学生姓名
    role: str
    school_id: int | None
    created_at: datetime  # 使用datetime类型，然后通过序列化转换为字符串

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        """将datetime序列化为ISO 8601格式字符串"""
        return dt.isoformat()

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
        nickname=user_data.nickname,  # 添加昵称
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


@router.get("/template", status_code=status.HTTP_200_OK)
async def download_student_template():
    """下载学生名单模板（Excel格式）"""
    import io
    import openpyxl
    from fastapi.responses import StreamingResponse

    # 创建工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学生名单模板"

    # 添加表头
    headers = ["学号", "姓名(昵称)", "密码"]
    ws.append(headers)

    # 添加示例数据
    example_data = [
        ["2024001", "张三", "123456"],
        ["2024002", "李四", "123456"],
        ["2024003", "王五", "123456"],
    ]
    for row in example_data:
        ws.append(row)

    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=student_template.xlsx"}
    )


@router.get("/export", status_code=status.HTTP_200_OK)
async def export_students(
    school_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """导出学生名单（Excel格式）"""
    import io
    import openpyxl
    from fastapi.responses import StreamingResponse

    # 构建查询
    query = db.query(User).filter(User.role == UserRole.STUDENT)

    # 权限控制
    if current_user.role == UserRole.SCHOOL_ADMIN:
        if school_id:
            query = query.filter(User.school_id == school_id)
        else:
            query = query.filter(User.school_id == current_user.school_id)
    elif school_id:
        query = query.filter(User.school_id == school_id)

    students = query.all()

    # 创建工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学生名单"

    # 添加表头
    headers = ["学号", "姓名(昵称)", "角色", "学校ID", "创建时间"]
    ws.append(headers)

    # 添加数据
    for student in students:
        row = [
            student.username,
            student.nickname or '-',
            student.role.value,
            student.school_id,
            student.created_at.strftime("%Y-%m-%d %H:%M")
        ]
        ws.append(row)

    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"students_{current_user.school_id if current_user.school_id else 'all'}_{current_user.id}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
    if user_data.nickname is not None:
        user.nickname = user_data.nickname
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


class BatchStudentCreate(BaseModel):
    """批量创建学生"""
    students: List[dict]
    # 每个学生包含：username(必填), nickname(可选), password(可选)
    # 如果不提供password，会自动生成
    auto_generate_password: bool = False
    # 如果不提供username，会自动生成学号
    auto_generate_username: bool = False


class BatchStudentResponse(BaseModel):
    """批量创建响应"""
    total: int
    success: int
    failed: int
    created_users: List[dict]


@router.post("/batch", response_model=BatchStudentResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_students(
    data: BatchStudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """批量创建学生"""
    # 学校管理员只能创建本校学生
    if current_user.role == UserRole.SCHOOL_ADMIN:
        # 检查所有学生的school_id是否在当前学校
        for student_data in data.students:
            if student_data.get('school_id') and student_data['school_id'] != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只能为本校创建学生"
                )

    total = len(data.students)
    success = 0
    failed = 0
    created_users = []

    for student_data in data.students:
        try:
            # 自动生成学号
            if data.auto_generate_username or not student_data.get('username'):
                username = _generate_student_id()
            else:
                username = student_data['username']

            # 自动生成密码
            if data.auto_generate_password or not student_data.get('password'):
                password = _generate_password()
            else:
                password = student_data['password']

            # 检查用户名是否已存在
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                failed += 1
                created_users.append({
                    'username': username,
                    'success': False,
                    'error': '用户名已存在'
                })
                continue

            # 创建用户
            from ..utils.security import get_password_hash
            new_user = User(
                username=username,
                password_hash=get_password_hash(password),
                nickname=student_data.get('nickname'),
                role=UserRole.STUDENT,
                school_id=student_data.get('school_id') or current_user.school_id
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            success += 1
            created_users.append({
                'id': new_user.id,
                'username': new_user.username,
                'nickname': new_user.nickname,
                'password': password,  # 返回密码供前端显示
                'success': True
            })
        except Exception as e:
            failed += 1
            created_users.append({
                'username': student_data.get('username', 'unknown'),
                'success': False,
                'error': str(e)
            })
            db.rollback()

    return BatchStudentResponse(
        total=total,
        success=success,
        failed=failed,
        created_users=created_users
    )


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_school_admin_or_above)
):
    """导入学生名单（从上传的Excel文件）"""
    from fastapi import UploadFile, File

    # 由于需要读取上传的文件，这里应该从请求中获取
    # 前端需要通过FormData上传Excel文件
    # 这个端点需要前端传递文件，这里只是定义接口
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="请使用前端导入功能上传Excel文件"
    )


def _generate_student_id() -> str:
    """生成学号（格式：2024XXXX）"""
    year = 2024
    random_num = random.randint(1000, 9999)
    return f"{year}{random_num}"


def _generate_password() -> str:
    """生成随机密码（8位，包含字母和数字）"""
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choice(chars) for _ in range(8))
    return password
