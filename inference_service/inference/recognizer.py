import torch
import numpy as np
from typing import List, Dict
import redis
import hashlib
from model.siamese_network import ModelManager
from preprocessing.image_processor import ImageProcessor
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class Recognizer:
    """识别器"""
    
    def __init__(self):
        self.model_manager = ModelManager(settings.MODEL_DIR)
        self.image_processor = ImageProcessor()
        self.redis_client = None
        
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=False
            )
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis连接失败: {str(e)}")
            self.redis_client = None
    
    async def recognize(self, image_path: str, top_k: int = 5) -> Dict:
        """识别单张图片"""
        try:
            processed_image, extracted_path = self.image_processor.process_sample(
                image_path,
                separation_mode="auto"
            )
            
            image_tensor = torch.from_numpy(processed_image).permute(2, 0, 1).float()
            features = self.model_manager.extract_features(image_tensor)
            
            # TODO: 与数据库中的用户样本特征比较
            result = {
                "top_k": [
                    {"user_id": 1, "username": "test_user", "score": 0.95}
                ],
                "is_unknown": False,
                "confidence": 0.95
            }
            
            return result
        except Exception as e:
            logger.error(f"识别失败: {str(e)}")
            raise
    
    async def batch_recognize(self, image_paths: List[str], top_k: int = 5) -> List[Dict]:
        """批量识别"""
        results = []
        for image_path in image_paths:
            try:
                result = await self.recognize(image_path, top_k=top_k)
                results.append(result)
            except Exception as e:
                logger.error(f"识别失败: {str(e)}")
                results.append({
                    "top_k": [],
                    "is_unknown": True,
                    "confidence": 0.0,
                    "error": str(e)
                })
        return results
