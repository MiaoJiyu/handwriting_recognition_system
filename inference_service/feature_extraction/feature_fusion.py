import numpy as np
from typing import Union
from sklearn.decomposition import PCA
import logging
import pickle
import os
from .deep_features import DeepFeatureExtractor
from .traditional_features import TraditionalFeatureExtractor

logger = logging.getLogger(__name__)


class FeatureFusion:
    """特征融合模块"""

    def __init__(
        self,
        deep_extractor: DeepFeatureExtractor = None,
        traditional_extractor: TraditionalFeatureExtractor = None,
        use_pca: bool = True,
        pca_dim: int = 256,
        pca_save_path: str = None
    ):
        self.deep_extractor = deep_extractor or DeepFeatureExtractor()
        self.traditional_extractor = traditional_extractor or TraditionalFeatureExtractor()
        self.use_pca = use_pca
        self.pca_dim = pca_dim
        self.pca = None
        self._pca_fitted = False
        self.pca_save_path = pca_save_path or "models/pca.pkl"

        # 尝试加载已保存的PCA
        self._load_pca()

    def _load_pca(self):
        """从文件加载PCA模型"""
        if os.path.exists(self.pca_save_path):
            try:
                with open(self.pca_save_path, 'rb') as f:
                    self.pca = pickle.load(f)
                self._pca_fitted = True
                logger.info(f"从 {self.pca_save_path} 加载PCA模型，n_components={self.pca.n_components}")
            except Exception as e:
                logger.warning(f"加载PCA模型失败: {str(e)}，将重新拟合")
                self.pca = None
                self._pca_fitted = False

    def _save_pca(self):
        """保存PCA模型到文件"""
        if self.pca is not None:
            os.makedirs(os.path.dirname(self.pca_save_path), exist_ok=True)
            with open(self.pca_save_path, 'wb') as f:
                pickle.dump(self.pca, f)
            logger.info(f"PCA模型已保存到 {self.pca_save_path}")
    
    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """归一化特征"""
        # L2归一化
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
        return features
    
    def extract_fused_features(
        self,
        image: Union[np.ndarray, list],
        normalize: bool = True
    ) -> np.ndarray:
        """
        提取融合特征

        Args:
            image: 输入图片或图片列表
            normalize: 是否归一化特征

        Returns:
            融合后的特征向量
        """
        if isinstance(image, list):
            # 批量处理
            deep_features = self.deep_extractor.extract_batch(image)
            traditional_features = self.traditional_extractor.extract_batch(image)
        else:
            # 单张图片
            deep_features = self.deep_extractor.extract(image)
            traditional_features = self.traditional_extractor.extract(image)

            # 确保是2D数组
            if len(deep_features.shape) == 1:
                deep_features = deep_features.reshape(1, -1)
            if len(traditional_features.shape) == 1:
                traditional_features = traditional_features.reshape(1, -1)

        # 归一化各个特征
        if normalize:
            for i in range(len(deep_features)):
                deep_features[i] = self._normalize_features(deep_features[i])
            for i in range(len(traditional_features)):
                traditional_features[i] = self._normalize_features(traditional_features[i])

        # 拼接特征
        fused_features = np.concatenate([deep_features, traditional_features], axis=1)

        # PCA降维 - 只有当样本数足够时才应用PCA
        if self.use_pca and len(fused_features) >= 2:
            fused_features = self._apply_pca(fused_features)
        elif self.use_pca and len(fused_features) == 1:
            # 如果只有1个样本，不应用PCA，直接返回原始特征
            logger.warning("只有1个样本，跳过PCA降维")

        # 最终归一化
        if normalize:
            for i in range(len(fused_features)):
                fused_features[i] = self._normalize_features(fused_features[i])

        # 如果是单张图片，返回1D数组
        if isinstance(image, np.ndarray) and len(image.shape) >= 2:
            return fused_features[0]

        return fused_features
    
    def _apply_pca(self, features: np.ndarray) -> np.ndarray:
        """应用PCA降维"""
        if self.pca is None:
            self.pca = PCA(n_components=self.pca_dim)

        if not self._pca_fitted:
            # 首次使用时，用当前特征拟合PCA
            # 注意：在实际应用中，应该用训练数据拟合PCA

            # 动态调整 n_components，确保不超过样本数和特征数
            n_samples, n_features = features.shape
            max_components = min(n_samples, n_features)
            actual_n_components = min(self.pca_dim, max_components)

            # 更新 PCA 的 n_components
            if actual_n_components != self.pca.n_components:
                self.pca = PCA(n_components=actual_n_components)

            self.pca.fit(features)
            self._pca_fitted = True

            # 保存PCA模型
            self._save_pca()

            logger.info(f"PCA fitted with {actual_n_components} components (samples={n_samples}, features={n_features})")

        return self.pca.transform(features)
    
    def fit_pca(self, training_features: np.ndarray):
        """用训练数据拟合PCA"""
        if self.pca is None:
            # 动态调整 n_components，确保不超过样本数和特征数
            n_samples, n_features = training_features.shape
            max_components = min(n_samples, n_features)
            actual_n_components = min(self.pca_dim, max_components)
            self.pca = PCA(n_components=actual_n_components)

        self.pca.fit(training_features)
        self._pca_fitted = True
    
    def extract_batch(self, images: list, normalize: bool = True) -> np.ndarray:
        """批量提取融合特征"""
        return self.extract_fused_features(images, normalize=normalize)
