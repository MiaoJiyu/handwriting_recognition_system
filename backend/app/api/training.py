from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from ..core.database import get_db
from ..models.training_job import TrainingJob, TrainingJobStatus
from ..models.model import Model
from ..utils.dependencies import require_teacher_or_above, get_current_user
from ..services.inference_client import InferenceClient

router = APIRouter(prefix="/api/training", tags=["训练管理"])


class TrainingJobResponse(BaseModel):
    id: int
    status: str
    progress: float
    model_version_id: int | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TrainingJobCreate(BaseModel):
    force_retrain: bool = False


@router.post("", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def start_training(
    training_data: TrainingJobCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_teacher_or_above)
):
    """启动训练任务"""
    from ..models.sample import Sample, SampleStatus
    pending_samples = db.query(Sample).filter(Sample.status == SampleStatus.PENDING).count()
    if pending_samples == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有待处理的样本"
        )
    
    running_job = db.query(TrainingJob).filter(
        TrainingJob.status == TrainingJobStatus.RUNNING
    ).first()
    if running_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已有训练任务正在运行"
        )
    
    job = TrainingJob(
        status=TrainingJobStatus.PENDING,
        progress=0.0
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    try:
        client = InferenceClient()
        await client.train_model(job.id, force_retrain=training_data.force_retrain)
    except Exception as e:
        job.status = TrainingJobStatus.FAILED
        job.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动训练失败: {str(e)}"
        )
    
    return job


@router.get("", response_model=List[TrainingJobResponse])
async def list_training_jobs(
    status: Optional[TrainingJobStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """列出训练任务"""
    query = db.query(TrainingJob)
    if status:
        query = query.filter(TrainingJob.status == status)
    
    jobs = query.order_by(TrainingJob.created_at.desc()).limit(50).all()
    return jobs


@router.get("/models", response_model=List[dict])
async def list_models(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """列出模型版本"""
    models = db.query(Model).order_by(Model.created_at.desc()).all()
    return [
        {
            "id": m.id,
            "version": m.version,
            "accuracy": m.accuracy,
            "training_samples_count": m.training_samples_count,
            "is_active": m.is_active,
            "created_at": m.created_at
        }
        for m in models
    ]
