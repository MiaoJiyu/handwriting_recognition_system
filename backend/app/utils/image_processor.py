import os
import cv2
import numpy as np
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("警告: PaddleOCR未安装，将使用OpenCV回退方案")
from PIL import Image
import json
from typing import Tuple, Optional, Dict, List
from ..core.config import settings


class ImageProcessor:
    """图像处理器，用于自动检测和裁剪手写区域"""

    def __init__(self):
        # 初始化PaddleOCR，使用中文英文模型，启用方向检测
        self.ocr = None
        if PADDLEOCR_AVAILABLE:
            try:
                self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')
                print("PaddleOCR初始化成功")
            except Exception as e:
                print(f"PaddleOCR初始化失败: {str(e)}")
                print("将使用OpenCV回退方案进行文本检测")
        else:
            print("使用OpenCV回退方案进行文本检测")

    def detect_text_regions(self, image_path: str) -> List[Dict]:
        """
        检测图像中的文本区域
        返回: 包含边界框的列表，每个边界框格式为 {'x': int, 'y': int, 'width': int, 'height': int}
        """
        try:
            if self.ocr:
                # 使用PaddleOCR检测文本
                # 直接调用ocr()方法，不需要额外的参数
                result = self.ocr.ocr(image_path)

                boxes = []
                if result and len(result) > 0:
                    for line in result[0]:
                        if line and len(line) > 0:
                            # 获取边界框坐标
                            # PaddleOCR返回格式: [[[x1, y1], [x2, y2], [x3, y3], [x4, y4]], ...]
                            points = line[0]

                            # 计算边界框的左上角和宽高
                            x_coords = [p[0] for p in points]
                            y_coords = [p[1] for p in points]

                            x_min = int(min(x_coords))
                            y_min = int(min(y_coords))
                            x_max = int(max(x_coords))
                            y_max = int(max(y_coords))

                            width = x_max - x_min
                            height = y_max - y_min

                            # 过滤掉太小的区域（可能是噪声）
                            if width > 20 and height > 20:
                                boxes.append({
                                    'x': x_min,
                                    'y': y_min,
                                    'width': width,
                                    'height': height
                                })
                return boxes
            else:
                # 使用OpenCV回退方案进行文本检测
                print("使用OpenCV进行文本检测")
                return self.detect_text_regions_opencv(image_path)

        except Exception as e:
            print(f"PaddleOCR文本检测失败: {str(e)}")
            # 如果PaddleOCR失败，尝试使用OpenCV回退
            print("尝试使用OpenCV回退方案")
            return self.detect_text_regions_opencv(image_path)

    def detect_text_regions_opencv(self, image_path: str) -> List[Dict]:
        """
        使用OpenCV进行文本区域检测（回退方案）

        简单策略：检测图像中的文本候选区域
        """
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                print(f"无法读取图像: {image_path}")
                return []

            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 查找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            boxes = []
            for contour in contours:
                # 获取轮廓的边界框
                x, y, w, h = cv2.boundingRect(contour)

                # 过滤掉太小的区域（可能是噪声）
                if w > 50 and h > 50:
                    boxes.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h)
                    })

            return boxes
        except Exception as e:
            print(f"OpenCV文本检测失败: {str(e)}")
            return []
    
    def find_bounding_box(self, boxes: List[Dict]) -> Optional[Dict]:
        """
        从多个文本区域找到包含所有区域的最小边界框
        返回: 合并后的边界框
        """
        if not boxes:
            return None
        
        # 初始化最小/最大值
        x_min = float('inf')
        y_min = float('inf')
        x_max = float('-inf')
        y_max = float('-inf')
        
        for box in boxes:
            x_min = min(x_min, box['x'])
            y_min = min(y_min, box['y'])
            x_max = max(x_max, box['x'] + box['width'])
            y_max = max(y_max, box['y'] + box['height'])
        
        # 添加一些边距
        margin = 10
        x_min = max(0, x_min - margin)
        y_min = max(0, y_min - margin)
        
        # 确保边界框在图像范围内（需要读取图像尺寸）
        
        return {
            'x': int(x_min),
            'y': int(y_min),
            'width': int(x_max - x_min),
            'height': int(y_max - y_min)
        }
    
    def crop_image(self, image_path: str, bbox: Dict, output_path: Optional[str] = None) -> Optional[str]:
        """
        根据边界框裁剪图像
        返回: 裁剪后的图像路径
        """
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                print(f"无法读取图像: {image_path}")
                return None

            height, width = image.shape[:2]

            # 确保边界框在图像范围内
            x = max(0, bbox['x'])
            y = max(0, bbox['y'])
            w = min(bbox['width'], width - x)
            h = min(bbox['height'], height - y)

            if w <= 0 or h <= 0:
                print("无效的边界框尺寸")
                return None

            # 裁剪图像
            cropped = image[y:y+h, x:x+w]

            # 生成输出路径
            if not output_path:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.join(settings.UPLOAD_DIR, 'cropped')
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}_cropped.jpg")

            # 保存裁剪后的图像
            cv2.imwrite(output_path, cropped)

            return output_path
        except Exception as e:
            print(f"裁剪图像失败: {str(e)}")
            return None

    def crop_image_by_bbox(self, image_path: str, bbox: Dict, sample_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """
        根据给定的边界框裁剪图像
        返回: (边界框, 裁剪后的图像路径)
        """
        cropped_path = self.crop_image(image_path, bbox)
        return bbox, cropped_path
    
    def auto_crop_sample(self, image_path: str, sample_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """
        自动裁剪样本图像
        返回: (边界框, 裁剪后的图像路径)
        """
        # 检测文本区域
        boxes = self.detect_text_regions(image_path)
        
        if not boxes:
            print("未检测到文本区域")
            return None, None
        
        # 找到包含所有文本的最小边界框
        bbox = self.find_bounding_box(boxes)
        
        if not bbox:
            print("无法计算边界框")
            return None, None
        
        # 生成裁剪后图像的路径
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_dir = os.path.join(settings.UPLOAD_DIR, 'cropped')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_cropped.jpg")
        
        # 裁剪图像
        cropped_path = self.crop_image(image_path, bbox, output_path)
        
        if not cropped_path:
            print("裁剪失败")
            return None, None
        
        return bbox, cropped_path


# 全局图像处理器实例
image_processor = ImageProcessor()


def auto_crop_sample_image(image_path: str, sample_id: int, bbox: Optional[Dict] = None) -> Tuple[Optional[Dict], Optional[str]]:
    """
    裁剪样本图像的便捷函数
    如果提供了bbox，使用给定的裁剪区域；否则自动检测
    返回: (边界框, 裁剪后的图像路径)
    """
    if bbox:
        # 使用给定的裁剪区域
        return image_processor.crop_image_by_bbox(image_path, bbox, sample_id)
    else:
        # 自动检测裁剪区域
        return image_processor.auto_crop_sample(image_path, sample_id)