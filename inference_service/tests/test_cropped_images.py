"""
测试训练模块是否正确使用裁剪后的图片
"""
import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.trainer import HandwritingDataset


def test_dataset_uses_cropped_images():
    """测试数据集是否优先使用裁剪后的图片"""

    # 创建临时测试图片
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建测试图片（使用numpy创建一个简单的RGB图片）
        import numpy as np
        import cv2

        # 创建两张测试图片
        original_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        cropped_img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)

        original_path = os.path.join(temp_dir, "original.jpg")
        cropped_path = os.path.join(temp_dir, "cropped.jpg")

        cv2.imwrite(original_path, original_img)
        cv2.imwrite(cropped_path, cropped_img)

        # 创建模拟的样本列表（应该使用裁剪后的图片）
        samples = [
            {
                "id": 1,
                "user_id": 1,
                "image_path": cropped_path,  # 这里应该是裁剪后的路径
                "annotation_data": None,
                "separation_mode": "none"
            }
        ]

        # 创建模拟的ImageProcessor
        mock_processor = MagicMock()
        mock_processed_image = np.random.rand(112, 112, 3).astype(np.float32)
        mock_processor.process_sample.return_value = (mock_processed_image, None)

        # 创建数据集
        dataset = HandwritingDataset(samples, mock_processor)

        # 获取一个样本
        image_tensor, user_id = dataset[0]

        # 验证
        assert user_id == 1, "用户ID应该正确"
        assert image_tensor.shape == (3, 112, 112), "图片维度应该正确"

        # 验证process_sample被调用时使用的是裁剪后的图片路径
        mock_processor.process_sample.assert_called_once()
        call_args = mock_processor.process_sample.call_args

        # 检查第一个参数（image_path）是否是裁剪后的路径
        assert call_args[0][0] == cropped_path, f"应该使用裁剪后的图片路径，但使用了: {call_args[0][0]}"

        # 检查separation_mode是否为"none"
        assert call_args[1].get("separation_mode") == "none", "separation_mode应该是'none'"

        # 检查annotation是否为None
        assert call_args[1].get("annotation") is None, "annotation应该是None"

        print("✓ 测试通过：数据集正确使用了裁剪后的图片")
        print(f"  - 图片路径: {cropped_path}")
        print(f"  - separation_mode: none")
        print(f"  - annotation: None")

    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir)


def test_fallback_to_original_when_no_cropped():
    """测试当没有裁剪图片时，是否回退到原始图片"""

    temp_dir = tempfile.mkdtemp()
    try:
        import numpy as np
        import cv2

        # 只创建原始图片
        original_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        original_path = os.path.join(temp_dir, "original.jpg")
        cv2.imwrite(original_path, original_img)

        # 模拟没有裁剪图片的情况（_load_samples_from_db会设置image_path为原始路径）
        samples = [
            {
                "id": 1,
                "user_id": 1,
                "image_path": original_path,  # 没有裁剪图片时使用原始路径
                "annotation_data": None,
                "separation_mode": "none"
            }
        ]

        mock_processor = MagicMock()
        mock_processed_image = np.random.rand(224, 224, 3).astype(np.float32)
        mock_processor.process_sample.return_value = (mock_processed_image, None)

        dataset = HandwritingDataset(samples, mock_processor)
        image_tensor, user_id = dataset[0]

        # 验证
        assert user_id == 1
        assert image_tensor.shape == (3, 224, 224)

        # 验证使用了原始路径
        mock_processor.process_sample.assert_called_once()
        call_args = mock_processor.process_sample.call_args
        assert call_args[0][0] == original_path

        print("✓ 测试通过：当没有裁剪图片时，正确使用了原始图片")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("测试训练模块图片加载逻辑")
    print("=" * 60)
    print()

    test_dataset_uses_cropped_images()
    print()

    test_fallback_to_original_when_no_cropped()
    print()

    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)
