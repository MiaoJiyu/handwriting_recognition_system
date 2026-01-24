import cv2
import numpy as np
from typing import Dict
from skimage import feature
from skimage.filters import gabor


class TraditionalFeatureExtractor:
    """传统特征提取器"""
    
    def __init__(self):
        pass
    
    def extract_stroke_features(self, image: np.ndarray) -> np.ndarray:
        """提取笔画特征"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 计算笔画宽度（使用距离变换）
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        stroke_width = np.mean(dist_transform[dist_transform > 0]) if np.any(dist_transform > 0) else 0
        
        # 计算曲率（使用轮廓）
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        curvature = 0.0
        if len(contours) > 0:
            # 计算轮廓的曲率
            total_curvature = 0
            for contour in contours:
                if len(contour) > 2:
                    # 计算相邻点的角度变化
                    angles = []
                    for i in range(1, len(contour) - 1):
                        p1 = contour[i-1][0]
                        p2 = contour[i][0]
                        p3 = contour[i+1][0]
                        v1 = p2 - p1
                        v2 = p3 - p2
                        if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                            cos_angle = np.clip(cos_angle, -1, 1)
                            angle = np.arccos(cos_angle)
                            angles.append(angle)
                    if angles:
                        total_curvature += np.mean(angles)
            curvature = total_curvature / len(contours) if len(contours) > 0 else 0
        
        # 计算方向（使用梯度）
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        angles = np.arctan2(grad_y, grad_x)
        direction = np.mean(angles[~np.isnan(angles)])
        
        return np.array([stroke_width, curvature, direction])
    
    def extract_texture_features(self, image: np.ndarray) -> np.ndarray:
        """提取纹理特征（LBP）"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # 转换为uint8
        if gray.dtype != np.uint8:
            gray = (gray * 255).astype(np.uint8) if gray.max() <= 1.0 else gray.astype(np.uint8)
        
        # LBP特征
        radius = 3
        n_points = 8 * radius
        lbp = feature.local_binary_pattern(gray, n_points, radius, method='uniform')
        hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
        hist = hist.astype(float)
        hist /= (hist.sum() + 1e-7)  # 归一化
        
        # Gabor滤波器特征
        gabor_responses = []
        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            freq = 0.1
            gabor_filter_real, gabor_filter_imag = gabor(gray, frequency=freq, theta=theta)
            response = np.sqrt(gabor_filter_real**2 + gabor_filter_imag**2)
            gabor_responses.append(np.mean(response))
        
        return np.concatenate([hist, np.array(gabor_responses)])
    
    def extract_geometric_features(self, image: np.ndarray) -> np.ndarray:
        """提取几何特征"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # 转换为uint8
        if gray.dtype != np.uint8:
            gray = (gray * 255).astype(np.uint8) if gray.max() <= 1.0 else gray.astype(np.uint8)
        
        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 字符高度和宽度
        rows = np.where(np.any(binary == 0, axis=1))[0]
        cols = np.where(np.any(binary == 0, axis=0))[0]
        
        if len(rows) > 0 and len(cols) > 0:
            char_height = rows[-1] - rows[0] + 1
            char_width = cols[-1] - cols[0] + 1
        else:
            char_height = gray.shape[0]
            char_width = gray.shape[1]
        
        # 倾斜度（使用主成分分析）
        coords = np.column_stack(np.where(binary == 0))
        if len(coords) > 0:
            mean = np.mean(coords, axis=0)
            centered = coords - mean
            if len(centered) > 1:
                cov = np.cov(centered.T)
                eigenvals, eigenvecs = np.linalg.eigh(cov)
                if len(eigenvecs) > 0:
                    main_direction = eigenvecs[:, -1]
                    skew_angle = np.arctan2(main_direction[1], main_direction[0])
                else:
                    skew_angle = 0.0
            else:
                skew_angle = 0.0
        else:
            skew_angle = 0.0
        
        return np.array([char_height, char_width, skew_angle])
    
    def extract_statistical_features(self, image: np.ndarray) -> np.ndarray:
        """提取统计特征"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # 转换为uint8
        if gray.dtype != np.uint8:
            gray = (gray * 255).astype(np.uint8) if gray.max() <= 1.0 else gray.astype(np.uint8)
        
        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 笔画密度（非零像素比例）
        stroke_density = np.count_nonzero(binary == 0) / binary.size
        
        # 分布特征（水平和垂直投影）
        h_projection = np.sum(binary == 0, axis=1)
        v_projection = np.sum(binary == 0, axis=0)
        
        h_mean = np.mean(h_projection)
        h_std = np.std(h_projection)
        v_mean = np.mean(v_projection)
        v_std = np.std(v_projection)
        
        return np.array([stroke_density, h_mean, h_std, v_mean, v_std])
    
    def extract(self, image: np.ndarray) -> np.ndarray:
        """提取所有传统特征"""
        stroke_features = self.extract_stroke_features(image)
        texture_features = self.extract_texture_features(image)
        geometric_features = self.extract_geometric_features(image)
        statistical_features = self.extract_statistical_features(image)
        
        # 拼接所有特征
        all_features = np.concatenate([
            stroke_features,
            texture_features,
            geometric_features,
            statistical_features
        ])
        
        # 处理NaN和Inf
        all_features = np.nan_to_num(all_features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return all_features
    
    def extract_batch(self, images: list) -> np.ndarray:
        """批量提取特征"""
        features_list = []
        for image in images:
            features = self.extract(image)
            features_list.append(features)
        return np.array(features_list)
