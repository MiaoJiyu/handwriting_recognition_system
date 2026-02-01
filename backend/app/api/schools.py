from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..models.school import School
from ..utils.dependencies import require_system_admin, CurrentUserResponse

router = APIRouter(prefix="/schools", tags=["学校管理"])


class SchoolCreate(BaseModel):
    name: str


class SchoolUpdate(BaseModel):
    name: str


class SchoolResponse(BaseModel):
    id: int
    name: str
    created_at: str
    user_count: int = 0  # 该学校的用户数量

    class Config:
        from_attributes = True


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    school_data: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
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
    # 返回序列化后的数据
    return SchoolResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at.isoformat() if school.created_at else "",
        user_count=0
    )


@router.get("", response_model=List[SchoolResponse])
async def list_schools(
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """列出所有学校"""
    schools = db.query(School).all()
    result = []
    for school in schools:
        # 计算每个学校的用户数量
        user_count = db.query(School).filter(School.id == school.id).first() and \
                    len(school.users) if hasattr(school, 'users') else 0
        if not hasattr(school, 'users'):
            from ..models.user import User
            user_count = db.query(User).filter(User.school_id == school.id).count()
        result.append(SchoolResponse(
            id=school.id,
            name=school.name,
            created_at=school.created_at.isoformat() if school.created_at else "",
            user_count=user_count
        ))
    return result


@router.get("/{school_id}", response_model=SchoolResponse)
async def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """获取单个学校信息"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )
    from ..models.user import User
    user_count = db.query(User).filter(User.school_id == school_id).count()
    return SchoolResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at.isoformat() if school.created_at else "",
        user_count=user_count
    )


@router.put("/{school_id}", response_model=SchoolResponse)
async def update_school(
    school_id: int,
    school_data: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """更新学校信息（仅系统管理员）"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )

    # 检查学校名称是否已被其他学校使用
    if school_data.name != school.name:
        existing = db.query(School).filter(School.name == school_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="学校名称已存在"
            )

    school.name = school_data.name
    db.commit()
    db.refresh(school)

    from ..models.user import User
    user_count = db.query(User).filter(User.school_id == school_id).count()
    return SchoolResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at.isoformat() if school.created_at else "",
        user_count=user_count
    )


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """删除学校（仅系统管理员）"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学校不存在"
        )

    # 检查学校是否有关联用户
    from ..models.user import User
    user_count = db.query(User).filter(User.school_id == school_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该学校下有 {user_count} 个用户，无法删除"
        )

    db.delete(school)
    db.commit()
