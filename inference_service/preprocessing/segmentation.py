import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from .enhancement import Enhancement


class Segmentation:
    """打印/手写分离模块"""
    
    @staticmethod
    def separate_by_color(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """基于颜色分离打印和手写内容"""
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 打印内容通常是黑色或深色，手写可能是蓝色、红色等
        # 定义打印内容的颜色范围（黑色/深灰色）
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        mask_printed = cv2.inRange(hsv, lower_black, upper_black)
        
        # 手写内容通常是蓝色或红色
        # 蓝色范围
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 红色范围（需要处理红色在HSV中的两个范围）
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        # 合并手写内容mask
        mask_handwriting = cv2.bitwise_or(mask_blue, mask_red)
        
        # 提取区域
        printed_region = cv2.bitwise_and(image, image, mask=mask_printed)
        handwriting_region = cv2.bitwise_and(image, image, mask=mask_handwriting)
        
        return printed_region, handwriting_region
    
    @staticmethod
    def separate_by_texture(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """基于纹理分离打印和手写内容"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 使用Gabor滤波器检测纹理
        # 打印内容通常更规则，手写更不规则
        kernel_size = 21
        sigma = 5.0
        theta = np.pi / 4
        lambd = 10.0
        gamma = 0.5
        psi = 0
        
        gabor = cv2.getGaborKernel((kernel_size, kernel_size), sigma, theta, lambd, gamma, psi, ktype=cv2.CV_32F)
        filtered = cv2.filter2D(gray, cv2.CV_8UC3, gabor)
        
        # 二值化
        _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 打印内容通常更连续，手写更分散
        # 使用形态学操作分离
        kernel = np.ones((5, 5), np.uint8)
        printed_mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        handwriting_mask = cv2.bitwise_not(printed_mask)
        
        printed_region = cv2.bitwise_and(image, image, mask=printed_mask)
        handwriting_region = cv2.bitwise_and(image, image, mask=handwriting_mask)
        
        return printed_region, handwriting_region
    
    @staticmethod
    def separate_by_edge(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """基于边缘检测分离"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Canny边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 打印内容边缘更规则，手写边缘更不规则
        # 使用霍夫变换检测直线（打印内容通常有更多直线）
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)
        
        # 创建打印内容mask（直线区域）
        printed_mask = np.zeros_like(gray)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(printed_mask, (x1, y1), (x2, y2), 255, 3)
        
        # 手写内容mask（非直线区域）
        handwriting_mask = cv2.bitwise_not(printed_mask)
        handwriting_mask = cv2.bitwise_and(handwriting_mask, edges)
        
        printed_region = cv2.bitwise_and(image, image, mask=printed_mask)
        handwriting_region = cv2.bitwise_and(image, image, mask=handwriting_mask)
        
        return printed_region, handwriting_region
    
    @staticmethod
    def auto_detect_handwriting_region(image: np.ndarray) -> Optional[Dict]:
        """自动检测手写区域"""
        # 尝试多种方法，选择最佳结果
        methods = [
            Segmentation.separate_by_color,
            Segmentation.separate_by_texture,
            Segmentation.separate_by_edge
        ]
        
        best_region = None
        best_score = 0
        
        for method in methods:
            try:
                _, handwriting_region = method(image)
                
                # 计算手写区域的得分（非零像素比例）
                if len(handwriting_region.shape) == 3:
                    gray = cv2.cvtColor(handwriting_region, cv2.COLOR_BGR2GRAY)
                else:
                    gray = handwriting_region
                
                non_zero = np.count_nonzero(gray)
                total = gray.size
                score = non_zero / total if total > 0 else 0
                
                if score > best_score:
                    best_score = score
                    best_region = handwriting_region
            except Exception:
                continue
        
        if best_region is None:
            return None
        
        # 找到手写区域的边界框
        if len(best_region.shape) == 3:
            gray = cv2.cvtColor(best_region, cv2.COLOR_BGR2GRAY)
        else:
            gray = best_region
        
        # 找到非零像素的坐标
        coords = np.column_stack(np.where(gray > 0))
        
        if len(coords) == 0:
            return None
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        return {
            "bbox": {
                "x": int(x_min),
                "y": int(y_min),
                "width": int(x_max - x_min),
                "height": int(y_max - y_min)
            },
            "region": best_region[y_min:y_max+1, x_min:x_max+1]
        }
