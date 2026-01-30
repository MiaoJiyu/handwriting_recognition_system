"""
测试脚本 - 检查原始特征是否有区分度
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
import json
import numpy as np
from feature_extraction.feature_fusion import FeatureFusion
from preprocessing.image_processor import ImageProcessor
import cv2

# 数据库配置
DATABASE_URL = "mysql+pymysql://handwriting:Jiyu_1458485242@47.117.126.60:3306/handwriting_recognition?charset=utf8mb4"

def load_sample_images(limit=10):
    """从数据库加载样本图片"""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    image_processor = ImageProcessor()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT s.id, s.user_id, s.image_path, s.extracted_region_path, s.status
            FROM samples s
            WHERE s.status = 'PROCESSED'
            ORDER BY s.user_id
            LIMIT :limit
        """), {"limit": limit})

        samples = []
        for row in result:
            samples.append({
                "id": row[0],
                "user_id": row[1],
                "image_path": row[2],
                "extracted_region_path": row[3],
                "status": row[4]
            })

    return samples

def test_raw_features():
    """测试原始特征的区分度"""
    samples = load_sample_images(10)
    if not samples:
        print("没有找到样本")
        return

    print(f"加载了 {len(samples)} 个样本\n")

    # 不使用 PCA 的特征提取器
    feature_fusion = FeatureFusion(use_pca=False)

    # 收集每个用户的原始特征
    user_features = {}
    for sample in samples:
        user_id = sample["user_id"]

        # 使用extracted_region_path如果存在
        image_path = sample["extracted_region_path"] if sample["extracted_region_path"] else sample["image_path"]

        try:
            # 预处理图片
            processed_image, _ = ImageProcessor().process_sample(image_path, separation_mode="auto")

            # 提取原始特征（不归一化，不应用PCA）
            raw_features = feature_fusion._extract_raw_features(processed_image)

            if user_id not in user_features:
                user_features[user_id] = []
            user_features[user_id].append(raw_features[0])  # 取第一个（也是唯一的）特征

            print(f"User {user_id}, Sample {sample['id']}: "
                  f"raw_features shape={raw_features.shape}, "
                  f"mean={raw_features[0].mean():.6f}, std={raw_features[0].std():.6f}")

        except Exception as e:
            print(f"User {user_id}, Sample {sample['id']}: ERROR - {e}")

    print(f"\n共有 {len(user_features)} 个用户的特征\n")

    # 分析用户特征的区分度
    user_ids = list(user_features.keys())
    if len(user_ids) >= 2:
        print("用户特征之间的差异（原始特征，未应用PCA）:")
        for i in range(len(user_ids)):
            for j in range(i + 1, len(user_ids)):
                uid1, uid2 = user_ids[i], user_ids[j]
                f1 = user_features[uid1][0]
                f2 = user_features[uid2][0]

                diff = np.abs(f1 - f2)
                max_diff = diff.max()
                mean_diff = diff.mean()
                cosine_sim = np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))

                print(f"  User {uid1} vs User {uid2}: "
                      f"max_diff={max_diff:.8f}, mean_diff={mean_diff:.8f}, cosine={cosine_sim:.6f}")

if __name__ == '__main__':
    test_raw_features()
