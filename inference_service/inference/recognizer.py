import torch
import numpy as np
from typing import List, Dict, Optional
import redis
import hashlib
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model.siamese_network import ModelManager
from preprocessing.image_processor import ImageProcessor
from feature_extraction.feature_fusion import FeatureFusion
from matching.matcher import Matcher
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class Recognizer:
    """识别器"""
    
    def __init__(self):
        self.model_manager = ModelManager(settings.MODEL_DIR)
        self.image_processor = ImageProcessor()
        self.feature_fusion = FeatureFusion()
        self.matcher = Matcher()
        self.redis_client = None
        self.db_session = None
        
        # Redis缓存
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
        
        # 数据库连接（用于加载用户特征）
        try:
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            self.db_session = SessionLocal()
        except Exception as e:
            logger.warning(f"数据库连接失败: {str(e)}")
            self.db_session = None
    
    def _load_user_features(self) -> Dict[int, np.ndarray]:
        """从数据库加载用户特征"""
        if self.db_session is None:
            return {}
        
        try:
            # 直接使用SQL查询，避免导入backend模块
            from sqlalchemy import text
            
            result = self.db_session.execute(text("""
                SELECT uf.user_id, uf.feature_vector, u.username
                FROM user_features uf
                JOIN users u ON uf.user_id = u.id
            """))
            
            features_dict = {}
            for row in result:
                try:
                    user_id = row[0]
                    feature_vector_str = row[1]
                    # 解析特征向量
                    features = np.array(json.loads(feature_vector_str))
                    features_dict[user_id] = features
                except Exception as e:
                    logger.warning(f"加载用户 {row[0]} 的特征失败: {str(e)}")
                    continue
            
            return features_dict
        except Exception as e:
            logger.error(f"加载用户特征失败: {str(e)}")
            return {}
    
    async def recognize(self, image_path: str, top_k: int = 5) -> Dict:
        """识别单张图片"""
        try:
            # 预处理图片
            processed_image, extracted_path = self.image_processor.process_sample(
                image_path,
                separation_mode="auto"
            )
            
            # 提取融合特征
            query_features = self.feature_fusion.extract_fused_features(processed_image)
            
            # 加载用户特征库
            user_features_dict = self._load_user_features()
            
            # 匹配
            result = self.matcher.match(query_features, user_features_dict, top_k=top_k)
            
            # 添加用户名信息
            if self.db_session:
                try:
                    from sqlalchemy import text
                    for r in result["top_k"]:
                        user_result = self.db_session.execute(
                            text("SELECT username FROM users WHERE id = :user_id"),
                            {"user_id": r["user_id"]}
                        ).first()
                        if user_result:
                            r["username"] = user_result[0]
                        else:
                            r["username"] = f"user_{r['user_id']}"
                except Exception as e:
                    logger.warning(f"获取用户名失败: {str(e)}")
                    for r in result["top_k"]:
                        r["username"] = f"user_{r['user_id']}"
            else:
                for r in result["top_k"]:
                    r["username"] = f"user_{r['user_id']}"
            
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
