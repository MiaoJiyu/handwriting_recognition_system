"""
诊断脚本 - 检查用户特征是否有差异
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
import json
import numpy as np

# 数据库配置
DATABASE_URL = "mysql+pymysql://handwriting:Jiyu_1458485242@47.117.126.60:3306/handwriting_recognition?charset=utf8mb4"

def check_user_features():
    """检查数据库中的用户特征"""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT user_id, feature_vector FROM user_features'))

        features = {}
        for row in result:
            user_id = row[0]
            feature_str = row[1]
            try:
                feature = np.array(json.loads(feature_str))
                features[user_id] = feature
                print(f'User {user_id}: shape={feature.shape}, mean={feature.mean():.6f}, std={feature.std():.6f}')
                print(f'  first 5 values: {feature[:5]}')
            except Exception as e:
                print(f'User {user_id}: ERROR - {e}')

        print(f'\nTotal users with features: {len(features)}')

        # 检查是否所有特征都相同
        if len(features) >= 2:
            user_ids = list(features.keys())
            print(f'\n分析用户特征之间的差异:')
            for i in range(1, len(user_ids)):
                diff = np.abs(features[user_ids[i]] - features[user_ids[0]])
                max_diff = diff.max()
                mean_diff = diff.mean()
                cosine_sim = np.dot(features[user_ids[0]], features[user_ids[i]]) / (
                    np.linalg.norm(features[user_ids[0]]) * np.linalg.norm(features[user_ids[i]])
                )
                print(f'  User {user_ids[0]} vs User {user_ids[i]}: '
                      f'max_diff={max_diff:.8f}, mean_diff={mean_diff:.8f}, cosine={cosine_sim:.6f}')

        # 检查特征是否为零向量
        print(f'\n检查特征是否为常向量或零向量:')
        for user_id, feature in features.items():
            is_zero = np.allclose(feature, 0.0)
            is_constant = np.allclose(feature, feature[0]) if len(feature) > 0 else True
            print(f'  User {user_id}: is_zero={is_zero}, is_constant={is_constant}')

if __name__ == '__main__':
    check_user_features()
