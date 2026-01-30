import torch
import torch.nn as nn
import torchvision.models as models
from typing import Union
import numpy as np


class DeepFeatureExtractor:
    """深度学习特征提取器"""

    def __init__(self, model_manager = None):
        if model_manager is None:
            from core.config import settings
            from model.siamese_network import ModelManager
            # 禁用ImageNet预训练，因为预训练模型不是为字迹识别训练的
            self.model_manager = ModelManager(settings.MODEL_DIR, use_imagenet_pretrained=False)
        else:
            self.model_manager = model_manager
    
    def extract(self, image: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
        """
        提取深度特征
        
        Args:
            image: 输入图片 (numpy array或torch tensor)
                  如果是numpy array，形状应为 (H, W, 3) 或 (H, W)，值范围0-1
                  如果是torch tensor，形状应为 (C, H, W) 或 (1, C, H, W)
        
        Returns:
            特征向量 (numpy array, shape: (embedding_dim,))
        """
        # 转换为torch tensor
        if isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                # 灰度图转RGB
                image = np.stack([image, image, image], axis=2)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                # RGB格式
                pass
            else:
                raise ValueError(f"不支持的图片形状: {image.shape}")
            
            # 转换为 (C, H, W) 格式
            image_tensor = torch.from_numpy(image).permute(2, 0, 1).float()
        else:
            image_tensor = image
        
        # 确保值范围在0-1
        if image_tensor.max() > 1.0:
            image_tensor = image_tensor / 255.0
        
        # 提取特征
        features = self.model_manager.extract_features(image_tensor)
        
        # 转换为numpy array
        if isinstance(features, torch.Tensor):
            features = features.cpu().numpy()
        
        # 展平
        if len(features.shape) > 1:
            features = features.flatten()
        
        return features
    
    def extract_batch(self, images: list) -> np.ndarray:
        """批量提取特征"""
        features_list = []
        for image in images:
            features = self.extract(image)
            features_list.append(features)
        return np.array(features_list)
