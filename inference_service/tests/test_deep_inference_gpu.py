import numpy as np
import pytest
import torch

from feature_extraction.deep_features import DeepFeatureExtractor


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用，跳过 GPU 推理测试")
def test_deep_feature_extractor_gpu_outputs_normalized_embedding():
    extractor = DeepFeatureExtractor()

    img = np.random.rand(224, 224, 3).astype(np.float32)
    emb = extractor.extract(img)

    assert emb.ndim == 1
    assert emb.shape[0] == 512
    assert np.isfinite(emb).all()

    norm = np.linalg.norm(emb)
    assert 0.9 <= norm <= 1.1
