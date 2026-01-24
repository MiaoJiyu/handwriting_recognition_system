from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
import json
from ..core.database import get_db
from ..core.config import settings
from ..models.sample import Sample, SampleStatus, SampleRegion
from ..models.user import User
from ..utils.dependencies import get_current_user, require_teacher_or_above

router = APIRouter(prefix="/api/samples", tags=["样本管理"])


class SampleResponse(BaseModel):
    id: int
    user_id: int
    image_path: str
    original_filename: str
    status: str
    extracted_region_path: Optional[str]
    sample_metadata: Optional[str]
    uploaded_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SampleRegionResponse(BaseModel):
    id: int
    sample_id: int
    bbox: str
    is_auto_detected: int
    created_at: datetime

    class Config:
        from_attributes = True


class SampleDetailResponse(SampleResponse):
    sample_regions: List[SampleRegionResponse]


class CropRequest(BaseModel):
    bbox: dict  # {"x": 10, "y": 20, "width": 100, "height": 50}


@router.post("/upload", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
async def upload_sample(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传样本图片"""
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上传图片文件"
        )
    
    # 创建上传目录
    os.makedirs(settings.SAMPLES_DIR, exist_ok=True)
    
    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(settings.SAMPLES_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建样本记录
    sample = Sample(
        user_id=current_user.id,
        image_path=file_path,
        original_filename=file.filename,
        status=SampleStatus.PENDING
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    
    return sample


@router.get("", response_model=List[SampleResponse])
async def list_samples(
    user_id: Optional[int] = None,
    status: Optional[SampleStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取样本列表"""
    query = db.query(Sample)
    
    # 权限控制：学生只能查看自己的样本
    if current_user.role.value == "student":
        query = query.filter(Sample.user_id == current_user.id)
    elif user_id:
        query = query.filter(Sample.user_id == user_id)
    
    if status:
        query = query.filter(Sample.status == status)
    
    samples = query.order_by(Sample.uploaded_at.desc()).limit(limit).all()
    return samples


@router.get("/{sample_id}", response_model=SampleDetailResponse)
async def get_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取样本详情"""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )
    
    # 权限检查
    if current_user.role.value == "student" and sample.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看其他用户的样本"
        )
    
    return sample


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除样本"""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )
    
    # 权限检查
    if current_user.role.value == "student" and sample.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除其他用户的样本"
        )
    
    # 删除文件
    if os.path.exists(sample.image_path):
        os.remove(sample.image_path)
    if sample.extracted_region_path and os.path.exists(sample.extracted_region_path):
        os.remove(sample.extracted_region_path)
    
    db.delete(sample)
    db.commit()
    return None


@router.post("/{sample_id}/crop", response_model=SampleRegionResponse, status_code=status.HTTP_201_CREATED)
async def crop_sample_region(
    sample_id: int,
    crop_data: CropRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_above)
):
    """手动裁剪手写区域"""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )
    
    # 创建区域记录
    region = SampleRegion(
        sample_id=sample_id,
        bbox=json.dumps(crop_data.bbox),
        is_auto_detected=0  # 手动标注
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    
    return region
