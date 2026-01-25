import cv2
import numpy as np
from typing import Tuple


class Enhancement:
    """图像增强模块"""
    
    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """去噪"""
        # 使用非局部均值去噪
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    
    @staticmethod
    def binarize(image: np.ndarray, method: str = "adaptive") -> np.ndarray:
        """二值化"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if method == "adaptive":
            # 自适应阈值
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        elif method == "otsu":
            # Otsu阈值
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            # 固定阈值
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        return binary
    
    @staticmethod
    def deskew(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """倾斜校正"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 霍夫变换检测直线
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return image, 0.0
        
        # 计算平均角度
        # OpenCV 的 HoughLines 返回形状通常为 (N, 1, 2)；这里做兼容展开
        angles = []
        for line in lines[:20]:  # 只取前20条线
            try:
                rho, theta = line[0]
            except Exception:
                # 兜底：如果形状异常则跳过该条线
                continue
            angle = np.degrees(theta) - 90
            if -45 < angle < 45:
                angles.append(angle)
        
        if not angles:
            return image, 0.0
        
        avg_angle = np.mean(angles)
        
        # 旋转图像
        if abs(avg_angle) > 0.5:  # 只在校正角度大于0.5度时旋转
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated, avg_angle
        
        return image, 0.0
    
    @staticmethod
    def normalize_size(image: np.ndarray, target_size: Tuple[int, int] = (224, 224)) -> np.ndarray:
        """归一化尺寸"""
        return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
    
    @staticmethod
    def enhance(image: np.ndarray) -> np.ndarray:
        """综合增强处理"""
        # 去噪
        denoised = Enhancement.denoise(image)
        
        # 倾斜校正
        deskewed, _ = Enhancement.deskew(denoised)
        
        # 归一化尺寸
        normalized = Enhancement.normalize_size(deskewed)
        
        return normalized
