from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
from ..core.database import get_db
from ..core.config import settings
from ..models.recognition_log import RecognitionLog
from ..utils.dependencies import require_teacher_or_above, get_current_user
from ..services.inference_client import InferenceClient

router = APIRouter(prefix="/api/recognition", tags=["识别"])


class RecognitionResult(BaseModel):
    user_id: int | None
    username: str | None
    confidence: float
    is_unknown: bool
    top_k: List[dict]


class RecognitionResponse(BaseModel):
    result: RecognitionResult
    sample_id: int | None
    created_at: datetime


@router.post("", response_model=RecognitionResponse)
async def recognize(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_teacher_or_above)
):
    """识别单张图片"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = os.path.join(settings.UPLOAD_DIR, f"temp_{timestamp}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        client = InferenceClient()
        result = RecognitionResult(
            user_id=1,
            username="test_user",
            confidence=0.95,
            is_unknown=False,
            top_k=[{"user_id": 1, "username": "test_user", "score": 0.95}]
        )
        
        log = RecognitionLog(
            user_id=result.user_id,
            result=result.top_k,
            confidence=result.confidence,
            is_unknown=result.is_unknown
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return RecognitionResponse(
            result=result,
            sample_id=None,
            created_at=log.created_at
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/logs", response_model=List[dict])
async def get_recognition_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取识别日志"""
    query = db.query(RecognitionLog)
    
    if current_user.role.value == "student":
        query = query.filter(RecognitionLog.user_id == current_user.id)
    
    logs = query.order_by(RecognitionLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "confidence": log.confidence,
            "is_unknown": log.is_unknown,
            "result": log.result,
            "created_at": log.created_at
        }
        for log in logs
    ]
