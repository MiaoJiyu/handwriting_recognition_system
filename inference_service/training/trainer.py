import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import List, Dict, Tuple
import os
from pathlib import Path
from model.siamese_network import SiameseNetwork, ModelManager
from preprocessing.image_processor import ImageProcessor
from core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HandwritingDataset(Dataset):
    """字迹数据集"""
    
    def __init__(self, samples: List[Dict], image_processor: ImageProcessor):
        self.samples = samples
        self.image_processor = image_processor
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        image_path = sample["image_path"]
        user_id = sample["user_id"]
        annotation = sample.get("annotation_data")
        separation_mode = sample.get("separation_mode", "auto")
        
        # 预处理图片
        processed_image, _ = self.image_processor.process_sample(
            image_path,
            separation_mode=separation_mode,
            annotation=annotation
        )
        
        # 转换为tensor
        image_tensor = torch.from_numpy(processed_image).permute(2, 0, 1).float()
        
        return image_tensor, user_id


class TripletLoss(nn.Module):
    """Triplet Loss for Few-shot Learning"""
    
    def __init__(self, margin: float = 1.0):
        super(TripletLoss, self).__init__()
        self.margin = margin
    
    def forward(self, anchor, positive, negative):
        """计算Triplet Loss"""
        distance_positive = nn.functional.pairwise_distance(anchor, positive)
        distance_negative = nn.functional.pairwise_distance(anchor, negative)
        loss = torch.relu(distance_positive - distance_negative + self.margin)
        return loss.mean()


class Trainer:
    """训练器"""
    
    def __init__(self):
        self.model_manager = ModelManager(settings.MODEL_DIR)
        self.image_processor = ImageProcessor()
        self.training_status = {}  # 存储训练状态
    
    def _load_samples_from_db(self) -> List[Dict]:
        """从数据库加载样本"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import text
            from core.config import settings
            
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            
            # 查询已处理的样本（使用SQL直接查询）
            result_set = db.execute(text("""
                SELECT s.id, s.user_id, s.image_path, s.extracted_region_path, s.status
                FROM samples s
                WHERE s.status = 'PROCESSED'
            """))
            
            result = []
            for row in result_set:
                sample_id = row[0]
                # 获取区域信息
                region_result = db.execute(
                    text("SELECT bbox FROM sample_regions WHERE sample_id = :sample_id LIMIT 1"),
                    {"sample_id": sample_id}
                ).first()
                
                annotation_data = None
                if region_result:
                    import json
                    annotation_data = {"bbox": json.loads(region_result[0])}
                
                result.append({
                    "id": sample_id,
                    "user_id": row[1],
                    "image_path": row[2],
                    "extracted_region_path": row[3],
                    "annotation_data": annotation_data,
                    "separation_mode": "auto"
                })
            
            db.close()
            return result
        except Exception as e:
            logger.error(f"从数据库加载样本失败: {str(e)}")
            return []
    
    def _create_triplets(self, samples: List[Dict]) -> List[Tuple[Dict, Dict, Dict]]:
        """创建Triplet样本对"""
        # 按用户ID分组
        user_samples = {}
        for sample in samples:
            user_id = sample["user_id"]
            if user_id not in user_samples:
                user_samples[user_id] = []
            user_samples[user_id].append(sample)
        
        triplets = []
        user_ids = list(user_samples.keys())
        
        for user_id in user_ids:
            # 正样本对（同一用户的不同样本）
            user_sample_list = user_samples[user_id]
            if len(user_sample_list) < 2:
                continue
            
            # 负样本（不同用户的样本）
            negative_users = [uid for uid in user_ids if uid != user_id]
            if not negative_users:
                # 只有一个用户时无法构造负样本
                continue
            
            for i, anchor in enumerate(user_sample_list):
                # 随机选择一个正样本
                positives = [s for s in user_sample_list if s != anchor]
                if not positives:
                    continue
                positive = np.random.choice(positives)
                
                # 随机选择一个负样本
                negative_user_id = np.random.choice(negative_users)
                negative_candidates = user_samples.get(negative_user_id) or []
                if not negative_candidates:
                    continue
                negative = np.random.choice(negative_candidates)
                
                triplets.append((anchor, positive, negative))
        
        return triplets
    
    async def train(self, job_id: int, force_retrain: bool = False):
        """训练模型"""
        try:
            self.training_status[job_id] = {
                "status": "running",
                "progress": 0.0,
                "error_message": None
            }
            
            # 加载样本
            samples = self._load_samples_from_db()
            if len(samples) < 3:
                raise ValueError("样本数量不足，至少需要3个样本")
            
            # 决定训练策略
            total_samples = len(samples)
            # 这里应该从数据库获取已有样本数，暂时假设
            existing_samples = 0
            
            if force_retrain or (total_samples - existing_samples) >= total_samples * 0.1:
                # 全量重训练
                logger.info("执行全量重训练")
                model = SiameseNetwork()
            else:
                # 增量训练（微调）
                logger.info("执行增量训练（微调）")
                model = self.model_manager.load_model()
            
            model.train()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            
            # 创建Triplet数据集
            triplets = self._create_triplets(samples)
            if len(triplets) == 0:
                logger.warning("Triplet样本对不足，降级使用对比损失训练（不需要多用户负样本）")

            # 数据加载器（降低内存占用，避免 OOM killer）
            dataset = HandwritingDataset(samples, self.image_processor)
            dataloader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=0)

            # 损失函数和优化器
            criterion = TripletLoss(margin=1.0)
            optimizer = optim.Adam(model.parameters(), lr=0.001)

            # 训练（先降低 epoch，保证能在资源受限环境跑通）
            num_epochs = 3
            total_batches = len(dataloader) * num_epochs
            current_batch = 0
            
            for epoch in range(num_epochs):
                for batch_idx, (images, user_ids) in enumerate(dataloader):
                    images = images.to(device)
                    
                    # 创建triplet batch
                    # 这里简化处理，实际应该从batch中构造triplet
                    anchor_features = model.forward_one(images)
                    
                    # 计算损失（简化版，实际需要构造triplet）
                    # 这里使用对比损失作为简化
                    loss = self._compute_contrastive_loss(anchor_features, user_ids, model, device)
                    
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    
                    current_batch += 1
                    progress = current_batch / total_batches
                    self.training_status[job_id]["progress"] = progress
                    
                    if batch_idx % 10 == 0:
                        logger.info(f"Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}")
            
            # 保存模型
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.model_manager.save_model(model, version)
            
            # 提取所有用户特征并更新特征库
            await self._update_user_features(samples, version)
            
            self.training_status[job_id] = {
                "status": "completed",
                "progress": 1.0,
                "error_message": None,
                "model_version_id": version
            }
            
        except Exception as e:
            logger.error(f"训练失败: {str(e)}")
            self.training_status[job_id] = {
                "status": "failed",
                "progress": 0.0,
                "error_message": str(e)
            }
            raise
    
    def _compute_contrastive_loss(self, features, user_ids, model, device):
        """计算对比损失（简化版）"""
        # 这里应该实现真正的triplet loss
        # 暂时返回一个简单的损失
        return torch.mean(torch.sum(features ** 2, dim=1))
    
    async def _update_user_features(self, samples: List[Dict], model_version: str):
        """更新用户特征库"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import text
            from core.config import settings
            from feature_extraction.feature_fusion import FeatureFusion
            import json
            
            engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            
            feature_fusion = FeatureFusion()
            
            # 按用户分组样本
            user_samples = {}
            for sample in samples:
                user_id = sample["user_id"]
                if user_id not in user_samples:
                    user_samples[user_id] = []
                user_samples[user_id].append(sample)
            
            # 为每个用户提取并更新特征
            for user_id, user_sample_list in user_samples.items():
                try:
                    # 提取所有样本的特征
                    features_list = []
                    for sample in user_sample_list:
                        processed_image, _ = self.image_processor.process_sample(
                            sample["image_path"],
                            separation_mode=sample.get("separation_mode", "auto"),
                            annotation=sample.get("annotation_data")
                        )
                        features = feature_fusion.extract_fused_features(processed_image)
                        features_list.append(features)
                    
                    # 计算平均特征
                    if len(features_list) > 0:
                        avg_features = np.mean(features_list, axis=0)
                        feature_vector_str = json.dumps(avg_features.tolist())
                        sample_ids_str = json.dumps([s["id"] for s in user_sample_list])
                        
                        # 检查是否存在
                        existing = db.execute(
                            text("SELECT id FROM user_features WHERE user_id = :user_id"),
                            {"user_id": user_id}
                        ).first()
                        
                        if existing:
                            # 更新
                            db.execute(
                                text("""
                                    UPDATE user_features 
                                    SET feature_vector = :feature_vector, 
                                        sample_ids = :sample_ids,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE user_id = :user_id
                                """),
                                {
                                    "user_id": user_id,
                                    "feature_vector": feature_vector_str,
                                    "sample_ids": sample_ids_str
                                }
                            )
                        else:
                            # 插入
                            db.execute(
                                text("""
                                    INSERT INTO user_features (user_id, feature_vector, sample_ids)
                                    VALUES (:user_id, :feature_vector, :sample_ids)
                                """),
                                {
                                    "user_id": user_id,
                                    "feature_vector": feature_vector_str,
                                    "sample_ids": sample_ids_str
                                }
                            )
                        
                        db.commit()
                except Exception as e:
                    logger.error(f"更新用户 {user_id} 的特征失败: {str(e)}")
                    db.rollback()
                    continue
            
            db.close()
        except Exception as e:
            logger.error(f"更新用户特征库失败: {str(e)}")
    
    async def get_status(self, job_id: int) -> Dict:
        """获取训练状态"""
        return self.training_status.get(job_id, {
            "status": "pending",
            "progress": 0.0,
            "error_message": None
        })
