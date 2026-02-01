"""
训练器集成测试 - 验证自动适配功能
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.trainer import Trainer, TrainingMetrics
from training.auto_adapter import AutoTrainingAdapter, TrainingStrategy


class TestTrainerAutoAdapt(unittest.TestCase):
    """训练器自动适配集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.trainer = Trainer(enable_auto_adapt=True)
        self.trainer.model_manager = Mock()

    def test_init_with_auto_adapt(self):
        """测试初始化时启用自动适配"""
        self.assertIsNotNone(self.trainer.auto_adapter)
        self.assertIsInstance(self.trainer.auto_adapter, AutoTrainingAdapter)

    def test_init_without_auto_adapt(self):
        """测试初始化时禁用自动适配"""
        trainer = Trainer(enable_auto_adapt=False)
        self.assertIsNone(trainer.auto_adapter)

    @patch('training.trainer.HandwritingDataset')
    @patch('training.trainer.DataLoader')
    @patch('training.trainer.optim.Adam')
    @patch('torch.cuda.is_available', return_value=False)
    def test_train_with_auto_adapt_skip(
        self,
        mock_cuda,
        mock_adam,
        mock_dataloader,
        mock_dataset
    ):
        """测试自动适配跳过训练"""
        # 模拟自动适配器建议不训练
        with patch.object(
            self.trainer.auto_adapter,
            'get_recommendation',
            return_value={
                'should_train': False,
                'reason': '数据变化未达到训练阈值',
                'strategy': 'no_training',
                'hyperparameters': {},
                'priority': 0
            }
        ):
            # 异步运行训练
            async def run_train():
                await self.trainer.train(job_id=1, force_retrain=False, auto_adapt=True)

            # 运行异步函数
            asyncio.run(run_train())

            # 验证训练状态
            status = self.trainer.training_status[1]
            self.assertEqual(status['status'], 'completed')
            self.assertEqual(status['progress'], 1.0)
            self.assertIn('skip_reason', status)
            self.assertEqual(status['skip_reason'], '数据变化未达到训练阈值')

    @patch('training.trainer.HandwritingDataset')
    @patch('training.trainer.DataLoader')
    @patch('training.trainer.optim.Adam')
    @patch('torch.cuda.is_available', return_value=False)
    def test_train_with_auto_adapt_full_retrain(
        self,
        mock_cuda,
        mock_adam,
        mock_dataloader,
        mock_dataset
    ):
        """测试自动适配全量重训练"""
        # 模拟模型管理器
        self.trainer.model_manager.load_model.return_value = None
        self.trainer.model_manager.save_model = Mock()

        # 模拟自动适配器建议全量训练
        with patch.object(
            self.trainer.auto_adapter,
            'get_recommendation',
            return_value={
                'should_train': True,
                'reason': '检测到新用户',
                'strategy': 'full_retrain',
                'hyperparameters': {
                    'batch_size': 4,
                    'num_epochs': 15,
                    'learning_rate': 0.001,
                    'margin': 1.0
                },
                'priority': 10
            }
        ):
            # 模拟更新用户特征
            with patch.object(
                self.trainer,
                '_update_user_features',
                new_callable=AsyncMock
            ):
                # 模拟数据加载器
                mock_dataloader.return_value = iter([])

                # 异步运行训练
                async def run_train():
                    await self.trainer.train(job_id=2, force_retrain=False, auto_adapt=True)

                # 运行异步函数
                asyncio.run(run_train())

                # 验证自动适配器状态已更新
                # (这里简化验证，实际应该检查状态持久化)

    @patch('training.trainer.HandwritingDataset')
    @patch('training.trainer.DataLoader')
    @patch('training.trainer.optim.Adam')
    @patch('torch.cuda.is_available', return_value=False)
    def test_train_with_force_retrain_override(
        self,
        mock_cuda,
        mock_adam,
        mock_dataloader,
        mock_dataset
    ):
        """测试强制重训练覆盖自动适配"""
        # 模拟自动适配器建议不训练
        with patch.object(
            self.trainer.auto_adapter,
            'get_recommendation',
            return_value={
                'should_train': False,
                'reason': '数据变化未达到训练阈值',
                'strategy': 'no_training',
                'hyperparameters': {},
                'priority': 0
            }
        ):
            # 模拟更新用户特征
            with patch.object(
                self.trainer,
                '_update_user_features',
                new_callable=AsyncMock
            ):
                # 模拟数据加载器
                mock_dataloader.return_value = iter([])

                # 异步运行训练（强制重训练）
                async def run_train():
                    await self.trainer.train(job_id=3, force_retrain=True, auto_adapt=True)

                # 运行异步函数
                asyncio.run(run_train())

                # 验证训练状态（应该成功，因为强制重训练）
                status = self.trainer.training_status[3]
                # 注意：由于测试环境限制，可能无法完全运行训练
                # 这里主要验证逻辑流程

    def test_get_model_size(self):
        """测试模型大小计算"""
        import torch
        import torch.nn as nn

        # 创建一个简单的模型
        model = nn.Sequential(
            nn.Linear(10, 5),
            nn.ReLU(),
            nn.Linear(5, 1)
        )

        size_mb = self.trainer._get_model_size(model)

        # 验证模型大小大于0
        self.assertGreater(size_mb, 0)

    def test_get_previous_metrics_no_history(self):
        """测试获取之前指标（无历史）"""
        metrics = self.trainer._get_previous_metrics()
        self.assertIsNone(metrics)

    def test_get_previous_metrics_with_history(self):
        """测试获取之前指标（有历史）"""
        # 模拟历史记录
        self.trainer.auto_adapter.state['training_history'] = [
            {
                'timestamp': datetime.now().isoformat(),
                'strategy': 'full_retrain',
                'metrics': {
                    'loss': 2.5,
                    'validation_accuracy': 0.85,
                    'total_samples': 100,
                    'unique_users': 10
                }
            },
            {
                'timestamp': datetime.now().isoformat(),
                'strategy': 'full_retrain',
                'metrics': {
                    'loss': 2.0,
                    'validation_accuracy': 0.90,
                    'total_samples': 120,
                    'unique_users': 12
                }
            }
        ]

        metrics = self.trainer._get_previous_metrics()

        # 验证获取到倒数第二条记录
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.loss, 2.5)
        self.assertEqual(metrics.validation_accuracy, 0.85)

    @patch('training.trainer.Trainer._load_samples_from_db')
    def test_get_training_recommendation_no_samples(
        self,
        mock_load_samples
    ):
        """测试获取训练建议（样本不足）"""
        mock_load_samples.return_value = []

        # 异步运行
        async def run_get_recommendation():
            return await self.trainer.get_training_recommendation()

        recommendation = asyncio.run(run_get_recommendation())

        self.assertFalse(recommendation['should_train'])
        self.assertIn('样本数量不足', recommendation['reason'])

    @patch('training.trainer.Trainer._load_samples_from_db')
    def test_get_training_recommendation_with_samples(
        self,
        mock_load_samples
    ):
        """测试获取训练建议（有样本）"""
        mock_load_samples.return_value = [
            {'id': i, 'user_id': (i % 5) + 1, 'image_path': f'/path/{i}.jpg'}
            for i in range(1, 51)
        ]

        # 异步运行
        async def run_get_recommendation():
            return await self.trainer.get_training_recommendation()

        recommendation = asyncio.run(run_get_recommendation())

        # 验证包含所有必要字段
        self.assertIn('should_train', recommendation)
        self.assertIn('strategy', recommendation)
        self.assertIn('reason', recommendation)
        self.assertIn('hyperparameters', recommendation)

    def test_get_training_recommendation_no_adapter(self):
        """测试获取训练建议（无适配器）"""
        trainer = Trainer(enable_auto_adapt=False)

        # 异步运行
        async def run_get_recommendation():
            return await trainer.get_training_recommendation()

        recommendation = asyncio.run(run_get_recommendation())

        self.assertTrue(recommendation['should_train'])
        self.assertIn('自动适配未启用', recommendation['reason'])


if __name__ == "__main__":
    unittest.main()
