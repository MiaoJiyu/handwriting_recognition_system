import numpy as np
from typing import List, Dict, Optional
from .similarity import SimilarityCalculator
from core.config import settings
import json


class Matcher:
    """匹配器 - 用于特征匹配和用户识别"""
    
    def __init__(
        self,
        similarity_threshold: float = None,
        gap_threshold: float = None,
        similarity_method: str = "cosine"
    ):
        self.similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD
        self.gap_threshold = gap_threshold or settings.GAP_THRESHOLD
        self.similarity_calculator = SimilarityCalculator()
        self.similarity_method = similarity_method
    
    def match(
        self,
        query_features: np.ndarray,
        user_features_dict: Dict[int, np.ndarray],
        top_k: int = 5
    ) -> Dict:
        """
        匹配查询特征与用户特征库
        
        Args:
            query_features: 查询特征向量
            user_features_dict: 用户特征字典 {user_id: feature_vector}
            top_k: 返回Top-K结果
        
        Returns:
            匹配结果字典
        """
        if len(user_features_dict) == 0:
            return {
                "top_k": [],
                "is_unknown": True,
                "confidence": 0.0
            }
        
        # 计算与所有用户的相似度
        similarities = []
        for user_id, user_features in user_features_dict.items():
            try:
                # 如果特征存储为JSON字符串，需要解析
                if isinstance(user_features, str):
                    user_features = np.array(json.loads(user_features))
                elif isinstance(user_features, list):
                    user_features = np.array(user_features)
                
                similarity = self.similarity_calculator.compute_similarity(
                    query_features,
                    user_features,
                    method=self.similarity_method
                )
                
                similarities.append({
                    "user_id": user_id,
                    "score": similarity
                })
            except Exception as e:
                # 如果特征提取失败，跳过该用户
                continue
        
        if len(similarities) == 0:
            return {
                "top_k": [],
                "is_unknown": True,
                "confidence": 0.0
            }
        
        # 按相似度排序
        similarities.sort(key=lambda x: x["score"], reverse=True)
        
        # 获取Top-K
        top_k_results = similarities[:top_k]
        
        # 判断是否为未知
        is_unknown = self._is_unknown(top_k_results)
        
        # 计算置信度
        confidence = top_k_results[0]["score"] if top_k_results else 0.0
        
        return {
            "top_k": top_k_results,
            "is_unknown": is_unknown,
            "confidence": confidence
        }
    
    def _is_unknown(self, top_k_results: List[Dict]) -> bool:
        """
        判断是否为未知用户
        
        Args:
            top_k_results: Top-K匹配结果
        
        Returns:
            是否为未知用户
        """
        if len(top_k_results) == 0:
            return True
        
        # 阈值1: 最高相似度 < 阈值
        max_similarity = top_k_results[0]["score"]
        if max_similarity < self.similarity_threshold:
            return True
        
        # 阈值2: Top-K平均相似度 < 阈值
        avg_similarity = np.mean([r["score"] for r in top_k_results])
        if avg_similarity < self.similarity_threshold:
            return True
        
        # 阈值3: 最高相似度与次高相似度的差距 < gap_threshold
        # 如果差距太小，说明匹配不确定
        if len(top_k_results) >= 2:
            gap = top_k_results[0]["score"] - top_k_results[1]["score"]
            if gap < self.gap_threshold:
                return True
        
        return False
    
    def batch_match(
        self,
        query_features_list: List[np.ndarray],
        user_features_dict: Dict[int, np.ndarray],
        top_k: int = 5
    ) -> List[Dict]:
        """批量匹配"""
        results = []
        for query_features in query_features_list:
            result = self.match(query_features, user_features_dict, top_k=top_k)
            results.append(result)
        return results
