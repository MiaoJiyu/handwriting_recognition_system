import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import List, Dict, Tuple, Optional
import os
from pathlib import Path
from model.siamese_network import SiameseNetwork, ModelManager
from preprocessing.image_processor import ImageProcessor
from core.config import settings
import logging
from datetime import datetime
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .auto_adapter import AutoTrainingAdapter, TrainingMetrics, TrainingStrategy

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
        separation_mode = sample.get("separation_mode", "none")

        # 预处理图片（已裁剪的图片直接加载，不做区域分离）
        processed_image, _ = self.image_processor.process_sample(
            image_path,
            separation_mode=separation_mode,
            annotation=None  # 已裁剪的图片不需要annotation
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

    def __init__(self, enable_auto_adapt: bool = True):
        self.model_manager = ModelManager(settings.MODEL_DIR)
        self.image_processor = ImageProcessor()
        self.training_status = {}  # 存储训练状态
        self.auto_adapter = AutoTrainingAdapter() if enable_auto_adapt else None
        self.current_metrics = None  # 存储当前训练指标
    
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

            # 查询已处理的样本（优先使用裁剪后的图片）
            result_set = db.execute(text("""
                SELECT s.id, s.user_id, s.image_path, s.extracted_region_path, s.status
                FROM samples s
                WHERE s.status = 'PROCESSED'
            """))

            result = []
            for row in result_set:
                sample_id = row[0]

                # 优先使用已裁剪的图片路径
                image_path = row[3] or row[2]  # extracted_region_path 优先

                # 获取区域信息（用于fallback）
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
                    "image_path": image_path,
                    "annotation_data": annotation_data,
                    "separation_mode": "none"  # 已裁剪图片不需要再分离
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
    
    async def train(self, job_id: int, force_retrain: bool = False, auto_adapt: bool = True):
        """训练模型

        Args:
            job_id: 任务ID
            force_retrain: 是否强制重训练
            auto_adapt: 是否使用自动适配（默认True）
        """
        try:
            self.training_status[job_id] = {
                "status": "running",
                "progress": 0.0,
                "error_message": None
            }

            # 加载样本 (0% - 10%)
            self.training_status[job_id]["progress"] = 0.05
            samples = self._load_samples_from_db()
            if len(samples) < 3:
                raise ValueError("样本数量不足，至少需要3个样本")
            self.training_status[job_id]["progress"] = 0.10

            # 自动适配分析 (10% - 20%)
            if auto_adapt and self.auto_adapter and not force_retrain:
                logger.info("启用自动适配模式")
                recommendation = self.auto_adapter.get_recommendation(samples)
                self.training_status[job_id]["progress"] = 0.15

                logger.info(f"自动适配建议: {recommendation}")

                # 如果建议不训练，直接返回
                if not recommendation.get("should_train", True):
                    logger.info(f"自动适配建议不训练: {recommendation['reason']}")
                    self.training_status[job_id] = {
                        "status": "completed",
                        "progress": 1.0,
                        "error_message": None,
                        "model_version_id": None,
                        "skip_reason": recommendation.get("reason", "自动适配建议不训练")
                    }
                    return

                # 使用建议的超参数
                hyperparameters = recommendation.get("hyperparameters", {})
                strategy = recommendation.get("strategy", "full_retrain")

                logger.info(f"使用自动适配策略: {strategy}, 超参数: {hyperparameters}")
            else:
                hyperparameters = {}
                strategy = "full_retrain" if force_retrain else "incremental_fine_tune"
                logger.info(f"手动模式，策略: {strategy}")

            self.training_status[job_id]["progress"] = 0.20

            # 检查是否有已存在的训练模型
            existing_model = self.model_manager.load_model()
            total_samples = len(samples)

            # 决定训练策略
            if force_retrain or existing_model is None or strategy == "full_retrain":
                # 全量重训练 - 禁用ImageNet预训练，从头学习字迹特征
                logger.info("执行全量重训练（禁用ImageNet预训练）")
                model = SiameseNetwork(use_imagenet_pretrained=False)
            else:
                # 增量训练（微调）
                logger.info("执行增量训练（微调）")
                model = existing_model

            model.train()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)

            self.training_status[job_id]["progress"] = 0.25

            # 创建Triplet数据集
            triplets = self._create_triplets(samples)
            if len(triplets) == 0:
                logger.warning("Triplet样本对不足，降级使用对比损失训练（不需要多用户负样本）")

            # 数据加载器（使用动态batch_size）
            dataset = HandwritingDataset(samples, self.image_processor)
            batch_size = hyperparameters.get("batch_size", 4)
            logger.info(f"使用batch_size: {batch_size}")
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

            # 损失函数和优化器
            margin = hyperparameters.get("margin", 1.0)
            criterion = TripletLoss(margin=margin)

            learning_rate = hyperparameters.get("learning_rate", 0.001)
            optimizer = optim.Adam(model.parameters(), lr=learning_rate)

            self.training_status[job_id]["progress"] = 0.30

            # 训练（使用动态epoch数） - 30% - 80%
            num_epochs = hyperparameters.get("num_epochs", 15)
            total_batches = len(dataloader) * num_epochs
            current_batch = 0

            loss_history = []
            start_time = datetime.now()

            for epoch in range(num_epochs):
                epoch_losses = []
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
                    # 计算进度: 30% + (current_batch / total_batches) * 0.50 (30% -> 80%)
                    progress = 0.30 + (current_batch / total_batches) * 0.50
                    self.training_status[job_id]["progress"] = progress

                    epoch_losses.append(loss.item())

                    if batch_idx % 10 == 0:
                        logger.info(f"Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}")

                # 记录每个epoch的平均损失
                avg_epoch_loss = np.mean(epoch_losses)
                loss_history.append(avg_epoch_loss)
                logger.info(f"Epoch {epoch} 完成, 平均损失: {avg_epoch_loss:.4f}")

            # 计算训练指标 (80% - 85%)
            self.training_status[job_id]["progress"] = 0.80
            training_time = (datetime.now() - start_time).total_seconds()
            avg_loss = np.mean(loss_history)

            # 验证准确率估计（使用最后一个batch的损失）
            validation_accuracy = max(0.0, 1.0 - avg_loss)  # 简化估计

            # 创建指标对象
            metrics = TrainingMetrics(
                loss=avg_loss,
                validation_accuracy=validation_accuracy,
                training_time=training_time,
                model_size=self._get_model_size(model),
                total_samples=total_samples,
                unique_users=len(set(s["user_id"] for s in samples))
            )
            self.current_metrics = metrics

            logger.info(f"训练完成: {metrics}")

            # 自动评估（如果启用） (85% - 90%)
            self.training_status[job_id]["progress"] = 0.85
            if auto_adapt and self.auto_adapter:
                previous_metrics = self._get_previous_metrics()
                accepted, eval_message = self.auto_adapter.evaluate_training_result(
                    metrics,
                    previous_metrics
                )

                logger.info(f"自动评估结果: {eval_message}")

                if not accepted and not force_retrain:
                    logger.warning(f"训练结果未通过评估，回滚到之前的模型")
                    self.training_status[job_id] = {
                        "status": "failed",
                        "progress": 1.0,
                        "error_message": f"训练评估未通过: {eval_message}"
                    }
                    raise ValueError(f"训练评估未通过: {eval_message}")

            # 保存模型 (90% - 92%)
            self.training_status[job_id]["progress"] = 0.90
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use a smaller integer for model_version_id (timestamp in seconds)
            import time
            model_version_id = int(time.time())
            self.model_manager.save_model(model, version)
            self.training_status[job_id]["progress"] = 0.92

            # 提取所有用户特征并更新特征库 (92% - 99%)
            await self._update_user_features(samples, version, job_id)
            self.training_status[job_id]["progress"] = 0.99

            # 更新自动适配器状态
            if auto_adapt and self.auto_adapter:
                strategy_enum = TrainingStrategy(strategy)
                self.auto_adapter.update_training_state(samples, metrics, strategy_enum)

            self.training_status[job_id] = {
                "status": "completed",
                "progress": 1.0,
                "error_message": None,
                "model_version_id": model_version_id,
                "training_metrics": {
                    "loss": metrics.loss,
                    "validation_accuracy": metrics.validation_accuracy,
                    "training_time": metrics.training_time,
                    "total_samples": metrics.total_samples,
                    "unique_users": metrics.unique_users
                }
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
        """计算对比损失（改进版）"""
        # 将 features 和 user_ids 移动到同一个设备
        features = features.to(device)
        user_ids = user_ids.to(device)

        # 计算所有样本对之间的距离
        n = features.size(0)
        if n < 2:
            # 返回一个需要梯度的零张量
            return features.mean() * 0.0

        # 计算所有样本对之间的欧氏距离矩阵
        dist_matrix = torch.cdist(features, features)

        # 创建标签矩阵：如果两个样本是同一用户，则为1，否则为0
        labels = user_ids.unsqueeze(1) == user_ids.unsqueeze(0)
        labels = labels.float()

        # 计算正样本对距离和负样本对距离
        mask_positive = labels.clone()
        mask_negative = 1.0 - labels

        # 避免自比较（对角线）
        mask_eye = torch.eye(n, device=device)
        mask_positive = mask_positive * (1.0 - mask_eye)
        mask_negative = mask_negative * (1.0 - mask_eye)

        # 正样本对距离（同一用户的不同样本）
        pos_dist = (dist_matrix * mask_positive).sum() / (mask_positive.sum() + 1e-7)

        # 负样本对距离（不同用户的样本）
        neg_dist = (dist_matrix * mask_negative).sum() / (mask_negative.sum() + 1e-7)

        # Contrastive loss: L = (1-y) * 0.5 * d^2 + y * 0.5 * max(0, margin - d)^2
        margin = 1.0
        loss = (1.0 - labels) * 0.5 * dist_matrix ** 2 + \
                labels * 0.5 * torch.clamp(margin - dist_matrix, min=0) ** 2

        # 移除对角线（自比较）
        loss = loss * (1.0 - mask_eye)

        return loss.mean()
    
    async def _update_user_features(self, samples: List[Dict], model_version: str, job_id: int):
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

            # FeatureFusion 在循环外创建，避免PCA状态冲突
            feature_fusion = FeatureFusion()

            # 删除旧的PCA模型以确保使用新的PCA策略
            pca_path = "models/pca.pkl"
            if os.path.exists(pca_path):
                os.remove(pca_path)
                logger.info(f"删除旧的PCA模型: {pca_path}")
                # 重新创建FeatureFusion以清除PCA状态
                feature_fusion = FeatureFusion()

            # 按用户分组样本
            user_samples = {}
            for sample in samples:
                user_id = sample["user_id"]
                if user_id not in user_samples:
                    user_samples[user_id] = []
                user_samples[user_id].append(sample)

            # 首先收集所有训练样本用于PCA训练 (92% - 94%)
            self.training_status[job_id]["progress"] = 0.93
            all_training_images = []
            for user_sample_list in user_samples.values():
                for sample in user_sample_list:
                    # 使用已裁剪的图片（image_path已经是cropped path）
                    processed_image, _ = self.image_processor.process_sample(
                        sample["image_path"],
                        separation_mode="none",  # 已裁剪的图片不需要再分离
                        annotation=None
                    )
                    all_training_images.append(processed_image)

            # 使用所有训练样本提取原始特征（不归一化）
            logger.info(f"提取 {len(all_training_images)} 个训练样本的原始特征")
            raw_features_list = []
            for img in all_training_images:
                raw_features = feature_fusion._extract_raw_features(img)
                raw_features_list.append(raw_features)

            if len(raw_features_list) > 0:
                # 压缩维度：(m, 1, n) -> (m, n)
                features_array = np.squeeze(np.array(raw_features_list), axis=1)
                # 训练PCA
                logger.info(f"用 {features_array.shape[0]} 个样本，{features_array.shape[1]} 维特征训练PCA")
                feature_fusion.fit_pca(features_array)

            # 为每个用户提取并更新特征（使用已训练的PCA） (94% - 99%)
            total_users = len(user_samples)
            processed_users = 0
            for user_id, user_sample_list in user_samples.items():
                try:
                    # 批量预处理该用户的所有样本
                    processed_images = []
                    for sample in user_sample_list:
                        # 使用已裁剪的图片（image_path已经是cropped path）
                        processed_image, _ = self.image_processor.process_sample(
                            sample["image_path"],
                            separation_mode="none",  # 已裁剪的图片不需要再分离
                            annotation=None
                        )
                        processed_images.append(processed_image)

                    # 提取特征（PCA已训练，使用extract_batch避免重新拟合）
                    features_list = feature_fusion.extract_batch(processed_images)

                    # 计算平均特征
                    if len(features_list) > 0:
                        # 确保是2D数组
                        if len(features_list.shape) == 1:
                            features_list = features_list.reshape(1, -1)

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

                    # 更新进度: 94% + (processed_users / total_users) * 0.05 (94% -> 99%)
                    processed_users += 1
                    progress = 0.94 + (processed_users / total_users) * 0.05
                    self.training_status[job_id]["progress"] = progress

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

    def _get_model_size(self, model: torch.nn.Module) -> float:
        """获取模型大小（MB）"""
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        size_mb = (param_size + buffer_size) / 1024**2
        return size_mb

    def _get_previous_metrics(self) -> Optional[TrainingMetrics]:
        """获取之前的训练指标"""
        if self.auto_adapter and hasattr(self.auto_adapter, "state"):
            history = self.auto_adapter.state.get("training_history", [])
            if len(history) >= 2:  # 至少有一次历史记录
                last_entry = history[-2]
                metrics_data = last_entry.get("metrics", {})
                if metrics_data:
                    return TrainingMetrics(
                        loss=metrics_data.get("loss", 0.0),
                        validation_accuracy=metrics_data.get("validation_accuracy", 0.0),
                        training_time=0.0,  # 历史数据中没有
                        model_size=0.0,
                        total_samples=metrics_data.get("total_samples", 0),
                        unique_users=metrics_data.get("unique_users", 0)
                    )
        return None

    async def get_training_recommendation(self) -> Dict:
        """获取训练建议"""
        if not self.auto_adapter:
            return {
                "should_train": True,
                "reason": "自动适配未启用",
                "strategy": "full_retrain"
            }

        samples = self._load_samples_from_db()
        if len(samples) < 3:
            return {
                "should_train": False,
                "reason": "样本数量不足",
                "strategy": None
            }

        return self.auto_adapter.get_recommendation(samples)

    async def update_user_features_incremental(
        self,
        new_samples: List[Dict],
        user_id: int,
        use_existing_pca: bool = True
    ) -> bool:
        """
        增量更新用户特征（无需重新训练整个模型）

        Args:
            new_samples: 新上传的样本列表
            user_id: 要更新的用户ID
            use_existing_pca: 是否使用已拟合的PCA（推荐True）

        Returns:
            是否更新成功
        """
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

            # 加载现有特征
            existing_result = db.execute(
                text("SELECT feature_vector, sample_ids FROM user_features WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).first()

            if existing_result:
                # 如果已有特征，计算加权平均
                try:
                    old_features = np.array(json.loads(existing_result[0]))
                    old_sample_ids = json.loads(existing_result[1])
                except Exception as e:
                    logger.warning(f"解析用户 {user_id} 的现有特征失败: {str(e)}，将重新计算")
                    old_features = None
                    old_sample_ids = []
            else:
                old_features = None
                old_sample_ids = []

            # 提取新样本的特征
            processed_images = []
            for sample in new_samples:
                # 使用已裁剪的图片（image_path应该是cropped path）
                processed_image, _ = self.image_processor.process_sample(
                    sample["image_path"],
                    separation_mode="none",  # 已裁剪的图片不需要再分离
                    annotation=None
                )
                processed_images.append(processed_image)

            # 使用FeatureFusion提取特征
            feature_fusion = FeatureFusion()

            # 如果使用已拟合的PCA，确保不会重新拟合
            if use_existing_pca and not feature_fusion._pca_fitted:
                logger.warning(f"PCA未拟合，增量更新时将跳过PCA降维")
                feature_fusion.use_pca = False

            new_features_list = feature_fusion.extract_fused_features(processed_images)

            # 计算新特征的平均
            if len(new_features_list.shape) == 1:
                new_features_list = new_features_list.reshape(1, -1)

            new_avg_features = np.mean(new_features_list, axis=0)

            # 合并新旧特征（加权平均）
            if old_features is not None:
                # 权重：旧特征权重高（基于样本数量）
                old_weight = len(old_sample_ids)
                new_weight = len(new_samples)
                total_weight = old_weight + new_weight

                # 加权平均
                merged_features = (old_features * old_weight + new_avg_features * new_weight) / total_weight

                # 合并样本ID
                all_sample_ids = old_sample_ids + [s["id"] for s in new_samples]
            else:
                merged_features = new_avg_features
                all_sample_ids = [s["id"] for s in new_samples]

            # 更新数据库
            feature_vector_str = json.dumps(merged_features.tolist())
            sample_ids_str = json.dumps(all_sample_ids)

            if existing_result:
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
            db.close()

            logger.info(f"用户 {user_id} 的特征已增量更新（旧样本: {len(old_sample_ids)}, 新样本: {len(new_samples)}）")
            return True

        except Exception as e:
            logger.error(f"增量更新用户 {user_id} 的特征失败: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return False
