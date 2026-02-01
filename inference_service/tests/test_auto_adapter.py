"""
自动训练适配器测试
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.auto_adapter import (
    AutoTrainingAdapter,
    TrainingStrategy,
    DataChangeType,
    AdaptationDecision,
    TrainingMetrics
)


class TestAutoTrainingAdapter(unittest.TestCase):
    """自动训练适配器测试"""

    def setUp(self):
        """设置测试环境"""
        self.adapter = AutoTrainingAdapter(
            config_path="/tmp/test_adapter_config.json",
            min_samples_per_user=2,
            training_threshold=0.3,
            max_samples_for_full_retrain=1000
        )

        # 清理旧的测试文件
        if os.path.exists("/tmp/test_adapter_config.json"):
            os.remove("/tmp/test_adapter_config.json")
        if os.path.exists("/tmp/test_adapter_state.json"):
            os.remove("/tmp/test_adapter_state.json")

    def tearDown(self):
        """清理测试环境"""
        if os.path.exists("/tmp/test_adapter_config.json"):
            os.remove("/tmp/test_adapter_config.json")
        if os.path.exists("/tmp/test_adapter_state.json"):
            os.remove("/tmp/test_adapter_state.json")

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.adapter)
        self.assertEqual(self.adapter.min_samples_per_user, 2)
        self.assertEqual(self.adapter.training_threshold, 0.3)
        self.assertEqual(self.adapter.max_samples_for_full_retrain, 1000)

    def test_detect_data_changes_first_time(self):
        """测试首次数据变化检测"""
        # 创建测试样本
        samples = [
            {"id": 1, "user_id": 1, "image_path": "/path/1.jpg"},
            {"id": 2, "user_id": 1, "image_path": "/path/2.jpg"},
            {"id": 3, "user_id": 2, "image_path": "/path/3.jpg"},
        ]

        change_type, change_ratio, details = self.adapter.detect_data_changes(samples)

        self.assertEqual(change_type, DataChangeType.NEW_USERS)
        self.assertEqual(change_ratio, 1.0)
        self.assertEqual(details["new_samples"], 3)
        self.assertEqual(details["new_users"], 2)

    def test_detect_data_changes_new_samples(self):
        """检测新样本"""
        # 先设置状态
        self.adapter.state["last_sample_ids"] = [1, 2, 3]
        self.adapter.state["last_user_count"] = 2

        # 添加新样本
        samples = [
            {"id": 1, "user_id": 1, "image_path": "/path/1.jpg"},
            {"id": 2, "user_id": 1, "image_path": "/path/2.jpg"},
            {"id": 3, "user_id": 2, "image_path": "/path/3.jpg"},
            {"id": 4, "user_id": 1, "image_path": "/path/4.jpg"},
            {"id": 5, "user_id": 2, "image_path": "/path/5.jpg"},
        ]

        change_type, change_ratio, details = self.adapter.detect_data_changes(samples)

        self.assertEqual(change_type, DataChangeType.NEW_SAMPLES)
        self.assertAlmostEqual(change_ratio, 0.4)
        self.assertEqual(details["new_samples"], 2)

    def test_detect_data_changes_minor_change(self):
        """检测微小变化"""
        # 先设置状态
        self.adapter.state["last_sample_ids"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.adapter.state["last_user_count"] = 3

        # 只添加1个新样本
        samples = [
            {"id": i, "user_id": (i % 3) + 1, "image_path": f"/path/{i}.jpg"}
            for i in range(1, 12)
        ]

        change_type, change_ratio, details = self.adapter.detect_data_changes(samples)

        self.assertEqual(change_type, DataChangeType.NEW_SAMPLES)
        self.assertAlmostEqual(change_ratio, 0.1, places=1)

    def test_analyze_data_characteristics(self):
        """测试数据特征分析"""
        samples = [
            {"id": 1, "user_id": 1},
            {"id": 2, "user_id": 1},
            {"id": 3, "user_id": 2},
            {"id": 4, "user_id": 2},
            {"id": 5, "user_id": 3},
            {"id": 6, "user_id": 3},
            {"id": 7, "user_id": 3},
        ]

        characteristics = self.adapter.analyze_data_characteristics(samples)

        self.assertEqual(characteristics["total_samples"], 7)
        self.assertEqual(characteristics["unique_users"], 3)
        self.assertAlmostEqual(characteristics["avg_samples_per_user"], 7/3)
        self.assertEqual(characteristics["min_samples_per_user"], 2)
        self.assertEqual(characteristics["max_samples_per_user"], 3)
        self.assertTrue(characteristics["has_sufficient_samples"])

    def test_decide_training_strategy_new_users(self):
        """测试新用户时的训练策略决策"""
        data_characteristics = {
            "total_samples": 50,
            "unique_users": 5,
            "has_sufficient_samples": True
        }

        decision = self.adapter.decide_training_strategy(
            DataChangeType.NEW_USERS,
            1.0,
            data_characteristics
        )

        self.assertEqual(decision.strategy, TrainingStrategy.FULL_RETRAIN)
        self.assertEqual(decision.priority, 10)
        self.assertIn("新用户", decision.reason)
        self.assertFalse(decision.hyperparameters.get("use_imagenet_pretrained", True))

    def test_decide_training_strategy_new_samples_small(self):
        """测试小规模新样本的训练策略决策"""
        data_characteristics = {
            "total_samples": 500,
            "unique_users": 10,
            "has_sufficient_samples": True
        }

        decision = self.adapter.decide_training_strategy(
            DataChangeType.NEW_SAMPLES,
            0.5,
            data_characteristics
        )

        self.assertEqual(decision.strategy, TrainingStrategy.FULL_RETRAIN)
        self.assertEqual(decision.priority, 6)
        self.assertIn("全量训练", decision.reason)

    def test_decide_training_strategy_new_samples_large(self):
        """测试大规模新样本的训练策略决策"""
        data_characteristics = {
            "total_samples": 1500,
            "unique_users": 20,
            "has_sufficient_samples": True
        }

        decision = self.adapter.decide_training_strategy(
            DataChangeType.NEW_SAMPLES,
            0.4,
            data_characteristics
        )

        self.assertEqual(decision.strategy, TrainingStrategy.INCREMENTAL_FINE_TUNE)
        self.assertEqual(decision.priority, 4)
        self.assertIn("增量微调", decision.reason)
        self.assertEqual(decision.hyperparameters.get("learning_rate"), 0.0001)

    def test_decide_training_strategy_no_training(self):
        """测试无需训练的情况"""
        data_characteristics = {
            "total_samples": 100,
            "unique_users": 10,
            "has_sufficient_samples": True
        }

        decision = self.adapter.decide_training_strategy(
            DataChangeType.NEW_SAMPLES,
            0.05,  # 低于阈值
            data_characteristics
        )

        self.assertEqual(decision.strategy, TrainingStrategy.NO_TRAINING)
        self.assertEqual(decision.priority, 0)

    def test_calculate_hyperparameters_full_retrain(self):
        """测试全量重训练的超参数计算"""
        data_characteristics = {
            "total_samples": 500,
            "unique_users": 10
        }

        hyperparameters = self.adapter._calculate_hyperparameters(
            TrainingStrategy.FULL_RETRAIN,
            data_characteristics,
            0.5
        )

        self.assertEqual(hyperparameters["learning_rate"], 0.001)
        self.assertEqual(hyperparameters["use_imagenet_pretrained"], False)
        self.assertGreater(hyperparameters["batch_size"], 0)
        self.assertGreater(hyperparameters["num_epochs"], 0)

    def test_calculate_hyperparameters_incremental_fine_tune(self):
        """测试增量微调的超参数计算"""
        data_characteristics = {
            "total_samples": 1500,
            "unique_users": 20
        }

        hyperparameters = self.adapter._calculate_hyperparameters(
            TrainingStrategy.INCREMENTAL_FINE_TUNE,
            data_characteristics,
            0.4
        )

        self.assertEqual(hyperparameters["learning_rate"], 0.0001)
        self.assertEqual(hyperparameters["freeze_backbone"], True)
        self.assertGreater(hyperparameters["batch_size"], 0)
        self.assertGreater(hyperparameters["num_epochs"], 0)

    def test_evaluate_training_result_good(self):
        """测试良好训练结果的评估"""
        metrics = TrainingMetrics(
            loss=2.5,
            validation_accuracy=0.85,
            training_time=300.0,
            model_size=10.5,
            total_samples=100,
            unique_users=10
        )

        accepted, message = self.adapter.evaluate_training_result(metrics)

        self.assertTrue(accepted)
        self.assertIn("准确率良好", message)

    def test_evaluate_training_result_poor(self):
        """测试较差训练结果的评估"""
        metrics = TrainingMetrics(
            loss=15.0,
            validation_accuracy=0.3,
            training_time=300.0,
            model_size=10.5,
            total_samples=100,
            unique_users=10
        )

        accepted, message = self.adapter.evaluate_training_result(metrics)

        self.assertFalse(accepted)
        self.assertIn("损失值过高", message)

    def test_evaluate_training_result_with_previous(self):
        """测试与之前模型对比的评估"""
        previous_metrics = TrainingMetrics(
            loss=3.0,
            validation_accuracy=0.8,
            training_time=300.0,
            model_size=10.5,
            total_samples=100,
            unique_users=10
        )

        # 更好的结果
        current_metrics = TrainingMetrics(
            loss=2.0,
            validation_accuracy=0.9,
            training_time=350.0,
            model_size=10.5,
            total_samples=120,
            unique_users=12
        )

        accepted, message = self.adapter.evaluate_training_result(
            current_metrics,
            previous_metrics
        )

        self.assertTrue(accepted)
        self.assertIn("提升", message)

    def test_evaluate_training_result_with_previous_worse(self):
        """测试与之前模型对比的评估（更差的结果）"""
        previous_metrics = TrainingMetrics(
            loss=2.0,
            validation_accuracy=0.9,
            training_time=300.0,
            model_size=10.5,
            total_samples=100,
            unique_users=10
        )

        # 更差的结果
        current_metrics = TrainingMetrics(
            loss=3.0,
            validation_accuracy=0.75,  # 下降超过5%
            training_time=350.0,
            model_size=10.5,
            total_samples=120,
            unique_users=12
        )

        accepted, message = self.adapter.evaluate_training_result(
            current_metrics,
            previous_metrics
        )

        self.assertFalse(accepted)
        self.assertIn("下降", message)

    def test_get_recommendation_full_scenario(self):
        """测试完整训练建议流程"""
        samples = [
            {"id": i, "user_id": (i % 5) + 1, "image_path": f"/path/{i}.jpg"}
            for i in range(1, 51)  # 50个样本，5个用户
        ]

        recommendation = self.adapter.get_recommendation(samples)

        self.assertIn("should_train", recommendation)
        self.assertIn("strategy", recommendation)
        self.assertIn("reason", recommendation)
        self.assertIn("hyperparameters", recommendation)
        self.assertIn("change_type", recommendation)
        self.assertIn("change_ratio", recommendation)
        self.assertIn("data_characteristics", recommendation)

    def test_update_training_state(self):
        """测试训练状态更新"""
        samples = [
            {"id": 1, "user_id": 1},
            {"id": 2, "user_id": 2},
            {"id": 3, "user_id": 1},
        ]

        metrics = TrainingMetrics(
            loss=2.5,
            validation_accuracy=0.85,
            training_time=300.0,
            model_size=10.5,
            total_samples=3,
            unique_users=2
        )

        self.adapter.update_training_state(samples, metrics, TrainingStrategy.FULL_RETRAIN)

        # 验证状态更新
        self.assertIsNotNone(self.adapter.state["last_training_time"])
        self.assertEqual(self.adapter.state["last_sample_count"], 3)
        self.assertEqual(self.adapter.state["last_user_count"], 2)
        self.assertEqual(len(self.adapter.state["training_history"]), 1)

        # 验证历史记录
        history_entry = self.adapter.state["training_history"][0]
        self.assertEqual(history_entry["strategy"], "full_retrain")
        self.assertIn("metrics", history_entry)

    def test_state_persistence(self):
        """测试状态持久化"""
        samples = [
            {"id": 1, "user_id": 1},
            {"id": 2, "user_id": 2},
        ]

        metrics = TrainingMetrics(
            loss=2.5,
            validation_accuracy=0.85,
            training_time=300.0,
            model_size=10.5,
            total_samples=2,
            unique_users=2
        )

        self.adapter.update_training_state(samples, metrics, TrainingStrategy.FULL_RETRAIN)

        # 创建新的适配器实例，加载状态
        new_adapter = AutoTrainingAdapter(
            config_path="/tmp/test_adapter_config.json"
        )

        # 验证状态已加载
        self.assertEqual(new_adapter.state["last_sample_count"], 2)
        self.assertEqual(new_adapter.state["last_user_count"], 2)
        self.assertEqual(len(new_adapter.state["training_history"]), 1)


if __name__ == "__main__":
    unittest.main()
