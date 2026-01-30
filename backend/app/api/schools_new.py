from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from ..core.database import get_db
from ..models.school import School
from ..models.user import User
from ..utils.dependencies import require_system_admin, require_school_admin_or_above

router = APIRouter(prefix="/api/schools", tags=["学校管理"])


class SchoolCreate(BaseModel):
    name: str


class SchoolUpdate(BaseModel):
    name: Optional[str] = None


class SchoolResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class SchoolWithUsersResponse(SchoolResponse):
    """学校信息，包含用户统计"""
    total_users: int
    students_count: int
    teachers_count: int
    admins_count: int


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    school_data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_system_admin)
):
    """创建学校（仅系统管理员）"""
    existing = db.query(School).filter(School.name == school_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学校名称已存在"
        )

    school = School(name=school_data.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


@router.get("", response_model=List[SchoolWithUsersResponse])
async def list_schools(
    db: Session = Depends(get_db),
    current_user = Depends(require_school_admin_or_above)
):
    """列出所有学校（包含用户统计）"""
    schools = db.query(School).all()

    result = []
    for school in schools:
        # 统计用户数量
        total_users = db.query(User).filter(User.school_id == school.id).count()
        students_count = db.query(User).filter(User.school_id == school.id, User.role == "student").count()
        teachers_count = db.query(User).filter(User.school_id == school.id, User.role == "teacher").count()
        admins_count = db.query(User).filter(User.school_id == school.id, User.role == "school_admin").count()

        result.append(SchoolWithUsersResponse(
            id=school.id,
            name=school.name,
            created_at=school.created_at,
            total_users=total_users,
            students_count=students_count,
            teachers_count=teachers_count,
            admins_count=admins_count
        ))

    return result


@router.get("/{school_id}", response_model=SchoolWithUsersResponse)
async def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_school_admin_or_above)
):
    """获取学校详情"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )

    # 权限检查：学校管理员只能查看本校信息
    if current_user.role.value == "school_admin" and school.id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看其他学校信息"
        )

    # 统计用户数量
    total_users = db.query(User).filter(User.school_id == school.id).count()
    students_count = db.query(User).filter(User.school_id == school.id, User.role == "student").count()
    teachers_count = db.query(User).filter(User.school_id == school.id, User.role == "teacher").count()
    admins_count = db.query(User).filter(User.school_id == school.id, User.role == "school_admin").count()

    return SchoolWithUsersResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at,
        total_users=total_users,
        students_count=students_count,
        teachers_count=teachers_count,
        admins_count=admins_count
    )


@router.put("/{school_id}", response_model=SchoolResponse)
async def update_school(
    school_id: int,
    school_data: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_system_admin)
):
    """更新学校信息（仅系统管理员）"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )

    if school_data.name:
        # 检查名称是否已被其他学校使用
        existing = db.query(School).filter(
            School.name == school_data.name,
            School.id != school_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="学校名称已存在"
            )
        school.name = school_data.name

    db.commit()
    db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_system_admin)
):
    """删除学校（仅系统管理员）"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )

    # 检查是否有用户
    user_count = db.query(User).filter(User.school_id == school_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该学校还有{user_count}个用户，无法删除"
        )

    db.delete(school)
    db.commit()
    return None
