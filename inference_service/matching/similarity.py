import numpy as np
from typing import Union
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances


class SimilarityCalculator:
    """相似度计算器"""
    
    @staticmethod
    def cosine_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
        
        Returns:
            相似度值 (0-1)
        """
        # 确保是1D数组
        if len(features1.shape) > 1:
            features1 = features1.flatten()
        if len(features2.shape) > 1:
            features2 = features2.flatten()
        
        # 归一化
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        features1_norm = features1 / norm1
        features2_norm = features2 / norm2
        
        # 计算余弦相似度
        similarity = np.dot(features1_norm, features2_norm)
        
        # 归一化到0-1范围
        similarity = (similarity + 1) / 2
        
        return float(similarity)
    
    @staticmethod
    def euclidean_distance(features1: np.ndarray, features2: np.ndarray) -> float:
        """
        计算欧氏距离
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
        
        Returns:
            距离值（越小越相似）
        """
        # 确保是1D数组
        if len(features1.shape) > 1:
            features1 = features1.flatten()
        if len(features2.shape) > 1:
            features2 = features2.flatten()
        
        distance = np.linalg.norm(features1 - features2)
        return float(distance)
    
    @staticmethod
    def euclidean_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
        """
        将欧氏距离转换为相似度 (0-1)
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
        
        Returns:
            相似度值 (0-1)
        """
        distance = SimilarityCalculator.euclidean_distance(features1, features2)
        
        # 使用指数函数将距离转换为相似度
        # 距离越大，相似度越小
        similarity = np.exp(-distance / 10.0)  # 可调整除数来改变衰减速度
        
        return float(similarity)
    
    @staticmethod
    def manhattan_distance(features1: np.ndarray, features2: np.ndarray) -> float:
        """
        计算曼哈顿距离
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
        
        Returns:
            距离值
        """
        # 确保是1D数组
        if len(features1.shape) > 1:
            features1 = features1.flatten()
        if len(features2.shape) > 1:
            features2 = features2.flatten()
        
        distance = np.sum(np.abs(features1 - features2))
        return float(distance)
    
    @staticmethod
    def compute_similarity(
        features1: np.ndarray,
        features2: np.ndarray,
        method: str = "cosine"
    ) -> float:
        """
        计算相似度（统一接口）
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
            method: 计算方法 ("cosine", "euclidean", "manhattan")
        
        Returns:
            相似度值 (0-1)
        """
        if method == "cosine":
            return SimilarityCalculator.cosine_similarity(features1, features2)
        elif method == "euclidean":
            return SimilarityCalculator.euclidean_similarity(features1, features2)
        elif method == "manhattan":
            distance = SimilarityCalculator.manhattan_distance(features1, features2)
            return float(np.exp(-distance / 10.0))
        else:
            raise ValueError(f"不支持的相似度计算方法: {method}")
