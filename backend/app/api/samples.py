from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Form
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
import json
import threading
from ..core.database import get_db
from ..core.config import settings
from ..models.sample import Sample, SampleStatus, SampleRegion
from ..models.user import User
from ..utils.dependencies import get_current_user, require_teacher_or_above, CurrentUserResponse
from ..utils.validators import validate_upload_file
from ..utils.image_processor import auto_crop_sample_image

router = APIRouter(prefix="/samples", tags=["样本管理"])


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class SampleResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[UserInfo] = None  # 用户信息
    image_path: str
    image_url: str
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


class SampleUploadRequest(BaseModel):
    student_id: Optional[int] = None  # 目标学生ID，仅教师及以上权限可用


@router.post("/upload", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
async def upload_sample(
    request: Request,
    file: UploadFile = File(...),
    student_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """上传样本图片"""
    # 验证文件类型和大小
    await validate_upload_file(file, settings.MAX_UPLOAD_SIZE)

    # 确定目标用户ID
    target_user_id = current_user.id
    
    # 如果提供了student_id，验证权限并获取目标用户
    if student_id:
        # 只有教师及以上权限才能为其他用户上传样本
        if current_user.role not in ["teacher", "school_admin", "system_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权为其他用户上传样本"
            )
        
        try:
            target_user_id = int(student_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="student_id必须是有效的整数"
            )
        
        # 验证目标用户是否存在
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不存在"
            )
        
        # 学校管理员只能为同校用户上传样本
        if current_user.role == "school_admin" and current_user.school_id != target_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能为同校用户上传样本"
            )
    
    # 创建上传目录
    os.makedirs(settings.SAMPLES_DIR, exist_ok=True)
    
    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{target_user_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(settings.SAMPLES_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 对外暴露的访问路径（与 main.py 的 app.mount("/uploads", ...) 对齐）
    image_url = f"/uploads/samples/{filename}"

    # 创建样本记录
    sample = Sample(
        user_id=target_user_id,
        image_path=file_path,
        original_filename=file.filename,
        status=SampleStatus.PENDING
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)

    # 启动后台线程进行自动裁剪
    def process_auto_crop(sample_id: int, image_path: str):
        """后台处理自动裁剪"""
        from sqlalchemy.orm import sessionmaker
        from ..core.database import engine
        
        # 创建新的数据库会话
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        local_db = SessionLocal()
        
        try:
            print(f"开始自动裁剪样本 {sample_id}")
            
            # 调用自动裁剪函数
            bbox, cropped_path = auto_crop_sample_image(image_path, sample_id)
            
            if bbox and cropped_path:
                # 创建自动检测的区域记录
                region = SampleRegion(
                    sample_id=sample_id,
                    bbox=json.dumps(bbox),
                    is_auto_detected=1  # 自动检测
                )
                local_db.add(region)
                
                # 更新样本信息
                sample_record = local_db.query(Sample).filter(Sample.id == sample_id).first()
                if sample_record:
                    sample_record.status = SampleStatus.PROCESSED
                    sample_record.extracted_region_path = cropped_path
                    sample_record.processed_at = datetime.utcnow()
                
                local_db.commit()
                print(f"样本 {sample_id} 自动裁剪成功")
            else:
                print(f"样本 {sample_id} 自动裁剪失败")
                # 如果没有检测到文本区域，保持PENDING状态等待手动处理
                
        except Exception as e:
            print(f"样本 {sample_id} 自动裁剪处理异常: {str(e)}")
            local_db.rollback()
        finally:
            local_db.close()
    
    # 启动后台线程
    threading.Thread(target=process_auto_crop, args=(sample.id, sample.image_path), daemon=True).start()

    return SampleResponse(
        id=sample.id,
        user_id=sample.user_id,
        image_path=sample.image_path,
        image_url=str(request.base_url).rstrip('/') + image_url,
        original_filename=sample.original_filename,
        status=sample.status,
        extracted_region_path=sample.extracted_region_path,
        sample_metadata=getattr(sample, 'sample_metadata', None),
        uploaded_at=sample.uploaded_at,
        processed_at=getattr(sample, 'processed_at', None),
    )


@router.get("", response_model=List[SampleResponse])
async def list_samples(
    request: Request,
    user_id: Optional[int] = None,
    status: Optional[SampleStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """获取样本列表"""
    query = db.query(Sample).options(joinedload(Sample.user))

    # 权限控制：学生只能查看自己的样本
    if current_user.role == "student":
        query = query.filter(Sample.user_id == current_user.id)
    elif user_id:
        query = query.filter(Sample.user_id == user_id)

    if status:
        query = query.filter(Sample.status == status)

    samples = query.order_by(Sample.uploaded_at.desc()).limit(limit).all()

    base = str(request.base_url).rstrip('/')
    resp: List[SampleResponse] = []
    for s in samples:
        filename = os.path.basename(s.image_path)

        # 构建用户信息
        user_info = None
        if s.user:
            user_info = UserInfo(
                id=s.user.id,
                username=s.user.username,
                nickname=s.user.nickname,
                role=str(s.user.role)
            )

        resp.append(
            SampleResponse(
                id=s.id,
                user_id=s.user_id,
                user=user_info,
                image_path=s.image_path,
                image_url=f"{base}/uploads/samples/{filename}",
                original_filename=s.original_filename,
                status=s.status,
                extracted_region_path=s.extracted_region_path,
                sample_metadata=getattr(s, 'sample_metadata', None),
                uploaded_at=s.uploaded_at,
                processed_at=getattr(s, 'processed_at', None),
            )
        )
    return resp


@router.get("/{sample_id}", response_model=SampleDetailResponse)
async def get_sample(
    request: Request,
    sample_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """获取样本详情"""
    sample = db.query(Sample).options(joinedload(Sample.user)).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )

    # 权限检查
    if current_user.role == "student" and sample.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看其他用户的样本"
        )

    base = str(request.base_url).rstrip('/')
    filename = os.path.basename(sample.image_path)

    # 构建用户信息
    user_info = None
    if sample.user:
        user_info = UserInfo(
            id=sample.user.id,
            username=sample.user.username,
            nickname=sample.user.nickname,
            role=str(sample.user.role)
        )

    return SampleDetailResponse(
        id=sample.id,
        user_id=sample.user_id,
        user=user_info,
        image_path=sample.image_path,
        image_url=f"{base}/uploads/samples/{filename}",
        original_filename=sample.original_filename,
        status=sample.status,
        extracted_region_path=sample.extracted_region_path,
        sample_metadata=getattr(sample, 'sample_metadata', None),
        uploaded_at=sample.uploaded_at,
        processed_at=getattr(sample, 'processed_at', None),
        sample_regions=[
            SampleRegionResponse(
                id=r.id,
                sample_id=r.sample_id,
                bbox=r.bbox,
                is_auto_detected=r.is_auto_detected,
                created_at=r.created_at,
            )
            for r in getattr(sample, 'sample_regions', [])
        ],
    )


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """删除样本"""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )
    
    # 权限检查
    if current_user.role == "student" and sample.user_id != current_user.id:
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
    current_user: CurrentUserResponse = Depends(require_teacher_or_above)
):
    """手动裁剪手写区域"""
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="样本不存在"
        )

    # 查找是否已存在手动标注的区域
    existing_region = db.query(SampleRegion).filter(
        SampleRegion.sample_id == sample_id,
        SampleRegion.is_auto_detected == 0  # 只查找手动标注的
    ).first()

    bbox_json = json.dumps(crop_data.bbox)

    if existing_region:
        # 更新现有的手动标注区域
        existing_region.bbox = bbox_json
        db.flush()
        region = existing_region
    else:
        # 创建新的区域记录
        region = SampleRegion(
            sample_id=sample_id,
            bbox=bbox_json,
            is_auto_detected=0  # 手动标注
        )
        db.add(region)

    # 裁剪图片并保存
    try:
        cropped_path = auto_crop_sample_image(sample.image_path, sample_id, crop_data.bbox)
        if cropped_path:
            sample.extracted_region_path = cropped_path
    except Exception as e:
        print(f"裁剪图片失败: {str(e)}")

    # 裁剪/标注完成后，将样本标记为已处理，供训练服务读取
    sample.status = SampleStatus.PROCESSED
    sample.processed_at = datetime.utcnow()

    db.commit()
    db.refresh(region)

    return region
