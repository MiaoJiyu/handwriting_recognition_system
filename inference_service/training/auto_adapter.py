"""
自动训练适配器模块

自动检测训练需求并调整训练策略，实现深度模型的自动适配。
"""
import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)


class TrainingStrategy(Enum):
    """训练策略"""
    FULL_RETRAIN = "full_retrain"  # 全量重训练
    INCREMENTAL_FINE_TUNE = "incremental_fine_tune"  # 增量微调
    NO_TRAINING = "no_training"  # 无需训练


class DataChangeType(Enum):
    """数据变化类型"""
    NEW_USERS = "new_users"  # 新用户
    NEW_SAMPLES = "new_samples"  # 新样本
    SAMPLE_REMOVED = "sample_removed"  # 样本移除
    MINOR_CHANGE = "minor_change"  # 微小变化


@dataclass
class TrainingMetrics:
    """训练指标"""
    loss: float
    validation_accuracy: float
    training_time: float
    model_size: float
    total_samples: int
    unique_users: int


@dataclass
class AdaptationDecision:
    """适配决策"""
    strategy: TrainingStrategy
    reason: str
    hyperparameters: Dict[str, any]
    priority: int  # 优先级 (1-10, 10为最高)


class AutoTrainingAdapter:
    """
    自动训练适配器

    功能：
    1. 自动检测数据变化
    2. 智能选择训练策略
    3. 动态调整超参数
    4. 评估训练效果
    """

    def __init__(
        self,
        config_path: str = "./models/adapter_config.json",
        min_samples_per_user: int = 2,
        training_threshold: float = 0.3,  # 数据变化比例阈值
        max_samples_for_full_retrain: int = 1000
    ):
        """
        初始化自动训练适配器

        Args:
            config_path: 配置文件路径
            min_samples_per_user: 每用户最小样本数
            training_threshold: 触发训练的数据变化比例阈值
            max_samples_for_full_retrain: 触发全量重训练的最大样本数
        """
        self.config_path = config_path
        self.min_samples_per_user = min_samples_per_user
        self.training_threshold = training_threshold
        self.max_samples_for_full_retrain = max_samples_for_full_retrain

        self.state = {
            "last_training_time": None,
            "last_sample_count": 0,
            "last_user_count": 0,
            "last_sample_ids": [],
            "training_history": []
        }

        self._load_config()
        self._load_state()

    def _load_config(self):
        """加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"加载适配器配置: {self.config_path}")
            except Exception as e:
                logger.warning(f"加载配置失败，使用默认配置: {str(e)}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "min_samples_per_user": 2,
            "training_threshold": 0.3,
            "max_samples_for_full_retrain": 1000,
            "auto_train_enabled": True,
            "max_history_size": 10,
            "strategy_weights": {
                "full_retrain": 1.0,
                "incremental_fine_tune": 0.7,
                "no_training": 0.0
            }
        }

    def _save_config(self):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"保存适配器配置: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")

    def _load_state(self):
        """加载状态"""
        state_path = self.config_path.replace("config.json", "state.json")
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"加载适配器状态: {state_path}")
            except Exception as e:
                logger.warning(f"加载状态失败: {str(e)}")

    def _save_state(self):
        """保存状态"""
        state_path = self.config_path.replace("config.json", "state.json")
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"保存适配器状态: {state_path}")
        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")

    def detect_data_changes(
        self,
        current_samples: List[Dict],
        db_session=None
    ) -> Tuple[DataChangeType, float, Dict]:
        """
        检测数据变化

        Args:
            current_samples: 当前样本列表
            db_session: 数据库会话（用于获取更多信息）

        Returns:
            (变化类型, 变化比例, 详细信息)
        """
        current_sample_ids = set(s["id"] for s in current_samples)
        current_user_ids = set(s["user_id"] for s in current_samples)

        last_sample_ids = set(self.state["last_sample_ids"])
        last_user_count = self.state["last_user_count"]
        last_sample_count = self.state["last_sample_count"]

        # 首次训练
        if not last_sample_ids:
            return DataChangeType.NEW_USERS, 1.0, {
                "reason": "首次训练",
                "new_samples": len(current_samples),
                "new_users": len(current_user_ids)
            }

        # 计算变化
        new_samples = current_sample_ids - last_sample_ids
        removed_samples = last_sample_ids - current_sample_ids
        new_users = current_user_ids - set(range(1, last_user_count + 1))

        total_samples = len(current_samples)
        change_ratio = len(new_samples) / max(total_samples, 1)

        # 判断变化类型
        change_type = DataChangeType.MINOR_CHANGE
        details = {
            "new_samples": len(new_samples),
            "removed_samples": len(removed_samples),
            "new_users": len(new_users),
            "total_samples": total_samples,
            "change_ratio": change_ratio
        }

        if len(new_users) > 0:
            change_type = DataChangeType.NEW_USERS
            details["reason"] = f"新增 {len(new_users)} 个用户"
        elif len(new_samples) > 0:
            change_type = DataChangeType.NEW_SAMPLES
            details["reason"] = f"新增 {len(new_samples)} 个样本"
        elif len(removed_samples) > 0:
            change_type = DataChangeType.SAMPLE_REMOVED
            details["reason"] = f"移除 {len(removed_samples)} 个样本"

        logger.info(f"检测到数据变化: {change_type.value}, 比例={change_ratio:.2%}")
        return change_type, change_ratio, details

    def analyze_data_characteristics(
        self,
        samples: List[Dict]
    ) -> Dict:
        """
        分析数据特征

        Args:
            samples: 样本列表

        Returns:
            数据特征字典
        """
        # 按用户分组
        user_samples = {}
        for sample in samples:
            user_id = sample["user_id"]
            if user_id not in user_samples:
                user_samples[user_id] = []
            user_samples[user_id].append(sample)

        # 计算统计信息
        samples_per_user = [len(v) for v in user_samples.values()]
        user_count = len(user_samples)
        total_samples = len(samples)

        characteristics = {
            "total_samples": total_samples,
            "unique_users": user_count,
            "avg_samples_per_user": np.mean(samples_per_user) if samples_per_user else 0,
            "min_samples_per_user": min(samples_per_user) if samples_per_user else 0,
            "max_samples_per_user": max(samples_per_user) if samples_per_user else 0,
            "std_samples_per_user": np.std(samples_per_user) if samples_per_user else 0,
            "is_balanced": len(set(samples_per_user)) <= 2,  # 是否平衡
            "has_sufficient_samples": all(s >= self.min_samples_per_user for s in samples_per_user)
        }

        logger.info(f"数据特征分析: {characteristics}")
        return characteristics

    def decide_training_strategy(
        self,
        change_type: DataChangeType,
        change_ratio: float,
        data_characteristics: Dict
    ) -> AdaptationDecision:
        """
        决定训练策略

        Args:
            change_type: 数据变化类型
            change_ratio: 变化比例
            data_characteristics: 数据特征

        Returns:
            适配决策
        """
        strategy = TrainingStrategy.NO_TRAINING
        reason = "无需训练"
        hyperparameters = {}
        priority = 0

        # 检查是否需要训练
        needs_training = (
            change_ratio >= self.training_threshold or
            change_type in [DataChangeType.NEW_USERS, DataChangeType.SAMPLE_REMOVED]
        )

        if not needs_training:
            return AdaptationDecision(
                strategy=TrainingStrategy.NO_TRAINING,
                reason="数据变化未达到训练阈值",
                hyperparameters={},
                priority=0
            )

        total_samples = data_characteristics["total_samples"]

        # 选择策略
        if change_type == DataChangeType.NEW_USERS:
            # 新用户需要全量训练
            strategy = TrainingStrategy.FULL_RETRAIN
            reason = "检测到新用户，需要全量训练以学习新特征"
            priority = 10
        elif change_type == DataChangeType.SAMPLE_REMOVED:
            # 样本移除需要全量训练
            strategy = TrainingStrategy.FULL_RETRAIN
            reason = "检测到样本移除，需要全量训练以更新特征"
            priority = 8
        elif change_type == DataChangeType.NEW_SAMPLES:
            # 新样本根据数量选择策略
            if total_samples <= self.max_samples_for_full_retrain:
                strategy = TrainingStrategy.FULL_RETRAIN
                reason = "样本数量较少，使用全量训练以获得更好的特征"
                priority = 6
            else:
                strategy = TrainingStrategy.INCREMENTAL_FINE_TUNE
                reason = "样本数量较多，使用增量微调以提高效率"
                priority = 4

        # 计算超参数
        hyperparameters = self._calculate_hyperparameters(
            strategy,
            data_characteristics,
            change_ratio
        )

        logger.info(f"训练策略决策: {strategy.value}, 原因: {reason}")
        return AdaptationDecision(
            strategy=strategy,
            reason=reason,
            hyperparameters=hyperparameters,
            priority=priority
        )

    def _calculate_hyperparameters(
        self,
        strategy: TrainingStrategy,
        data_characteristics: Dict,
        change_ratio: float
    ) -> Dict:
        """
        计算超参数

        Args:
            strategy: 训练策略
            data_characteristics: 数据特征
            change_ratio: 变化比例

        Returns:
            超参数字典
        """
        total_samples = data_characteristics["total_samples"]
        unique_users = data_characteristics["unique_users"]

        # 基础超参数
        base_params = {
            "batch_size": 4,
            "num_epochs": 15,
            "learning_rate": 0.001,
            "margin": 1.0
        }

        if strategy == TrainingStrategy.FULL_RETRAIN:
            # 全量训练：根据样本数量调整
            batch_size = min(8, max(2, total_samples // 100))
            num_epochs = min(30, max(10, 20 - total_samples // 100))
            learning_rate = 0.001

            base_params.update({
                "batch_size": batch_size,
                "num_epochs": num_epochs,
                "learning_rate": learning_rate,
                "use_imagenet_pretrained": False  # 全量训练禁用ImageNet
            })

        elif strategy == TrainingStrategy.INCREMENTAL_FINE_TUNE:
            # 增量训练：更小的学习率和更少的epoch
            batch_size = min(8, max(2, total_samples // 50))
            num_epochs = min(10, max(5, 8 - total_samples // 200))
            learning_rate = 0.0001  # 更小的学习率

            base_params.update({
                "batch_size": batch_size,
                "num_epochs": num_epochs,
                "learning_rate": learning_rate,
                "freeze_backbone": True,  # 冻结骨干网络
                "use_imagenet_pretrained": None  # 保持原有模型
            })

        logger.info(f"计算超参数: {base_params}")
        return base_params

    def evaluate_training_result(
        self,
        metrics: TrainingMetrics,
        previous_metrics: Optional[TrainingMetrics] = None
    ) -> Tuple[bool, str]:
        """
        评估训练结果

        Args:
            metrics: 当前训练指标
            previous_metrics: 之前的训练指标

        Returns:
            (是否接受结果, 评估信息)
        """
        # 基础检查
        if metrics.loss > 10.0:
            return False, f"损失值过高: {metrics.loss:.4f}"

        if metrics.validation_accuracy < 0.5:
            return False, f"验证准确率过低: {metrics.validation_accuracy:.2%}"

        # 与之前对比
        if previous_metrics:
            accuracy_improvement = metrics.validation_accuracy - previous_metrics.validation_accuracy

            if accuracy_improvement < -0.05:
                return False, f"准确率下降超过5%: {accuracy_improvement:.2%}"

            if accuracy_improvement < 0:
                logger.warning(f"准确率轻微下降: {accuracy_improvement:.2%}")
                return True, f"准确率轻微下降但可接受: {accuracy_improvement:.2%}"

            if accuracy_improvement > 0.01:
                return True, f"准确率提升: {accuracy_improvement:.2%}"

            return True, f"准确率基本持平: {accuracy_improvement:.2%}"

        # 首次训练
        if metrics.validation_accuracy >= 0.7:
            return True, f"首次训练，准确率良好: {metrics.validation_accuracy:.2%}"
        else:
            return False, f"首次训练，准确率不足: {metrics.validation_accuracy:.2%}"

    def update_training_state(
        self,
        samples: List[Dict],
        metrics: TrainingMetrics,
        strategy: TrainingStrategy
    ):
        """
        更新训练状态

        Args:
            samples: 当前样本
            metrics: 训练指标
            strategy: 使用的策略
        """
        # 更新状态
        self.state["last_training_time"] = datetime.now().isoformat()
        self.state["last_sample_count"] = len(samples)
        self.state["last_user_count"] = len(set(s["user_id"] for s in samples))
        self.state["last_sample_ids"] = [s["id"] for s in samples]

        # 记录训练历史
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy.value,
            "metrics": {
                "loss": metrics.loss,
                "validation_accuracy": metrics.validation_accuracy,
                "total_samples": metrics.total_samples,
                "unique_users": metrics.unique_users
            }
        }

        self.state["training_history"].append(history_entry)

        # 限制历史记录大小
        max_history = self.config.get("max_history_size", 10)
        if len(self.state["training_history"]) > max_history:
            self.state["training_history"] = self.state["training_history"][-max_history:]

        self._save_state()
        logger.info(f"更新训练状态: strategy={strategy.value}, samples={metrics.total_samples}")

    def should_auto_train(self) -> bool:
        """
        检查是否应该自动训练

        Returns:
            是否应该自动训练
        """
        return self.config.get("auto_train_enabled", True)

    def get_recommendation(
        self,
        current_samples: List[Dict],
        db_session=None
    ) -> Dict:
        """
        获取训练建议

        Args:
            current_samples: 当前样本
            db_session: 数据库会话

        Returns:
            建议字典
        """
        # 检测数据变化
        change_type, change_ratio, change_details = self.detect_data_changes(
            current_samples,
            db_session
        )

        # 分析数据特征
        data_characteristics = self.analyze_data_characteristics(current_samples)

        # 决定策略
        decision = self.decide_training_strategy(
            change_type,
            change_ratio,
            data_characteristics
        )

        return {
            "should_train": decision.strategy != TrainingStrategy.NO_TRAINING,
            "strategy": decision.strategy.value,
            "reason": decision.reason,
            "hyperparameters": decision.hyperparameters,
            "priority": decision.priority,
            "change_type": change_type.value,
            "change_ratio": change_ratio,
            "change_details": change_details,
            "data_characteristics": data_characteristics
        }
