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
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上传图片文件"
        )

    # 验证文件大小
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小不能超过 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )
    # 重置文件指针到开头
    await file.seek(0)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = os.path.join(settings.UPLOAD_DIR, f"temp_{timestamp}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        client = InferenceClient()
        # 调用推理服务
        try:
            recognition_result = await client.recognize(temp_path)
            
            # 构建结果
            top_k = recognition_result.get("top_k", [])
            is_unknown = recognition_result.get("is_unknown", True)
            confidence = recognition_result.get("confidence", 0.0)
            
            user_id = None
            username = None
            if top_k and not is_unknown:
                user_id = top_k[0].get("user_id")
                username = top_k[0].get("username")
            
            result = RecognitionResult(
                user_id=user_id,
                username=username,
                confidence=confidence,
                is_unknown=is_unknown,
                top_k=top_k
            )
        except NotImplementedError:
            # 如果gRPC未实现，返回模拟结果
            result = RecognitionResult(
                user_id=None,
                username=None,
                confidence=0.0,
                is_unknown=True,
                top_k=[]
            )
        
        # 保存识别日志
        import json
        log = RecognitionLog(
            user_id=result.user_id,
            result=json.dumps(result.top_k, ensure_ascii=False),
            confidence=result.confidence,
            is_unknown=result.is_unknown,
            image_path=temp_path
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
