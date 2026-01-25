import numpy as np

from feature_extraction.deep_features import DeepFeatureExtractor


def test_deep_feature_extractor_cpu_outputs_normalized_embedding():
    extractor = DeepFeatureExtractor()

    # 随机生成一张 RGB 图片，值范围 0-1
    img = np.random.rand(224, 224, 3).astype(np.float32)

    emb = extractor.extract(img)

    assert isinstance(emb, np.ndarray)
    assert emb.ndim == 1
    assert emb.shape[0] == 512

    assert np.isfinite(emb).all()

    norm = np.linalg.norm(emb)
    # forward_one 中做了 L2 normalize，允许一定误差
    assert 0.9 <= norm <= 1.1
