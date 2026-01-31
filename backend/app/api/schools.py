from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..models.school import School
from ..utils.dependencies import require_system_admin, CurrentUserResponse

router = APIRouter(prefix="/api/schools", tags=["学校管理"])


class SchoolCreate(BaseModel):
    name: str


class SchoolResponse(BaseModel):
    id: int
    name: str
    created_at: str

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
    return school


@router.get("", response_model=List[SchoolResponse])
async def list_schools(
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(require_system_admin)
):
    """列出所有学校"""
    schools = db.query(School).all()
    return schools
