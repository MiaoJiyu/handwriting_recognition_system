import cv2
import numpy as np
from typing import Tuple, Optional, Dict
import os
import urllib.request
from urllib.parse import urljoin
from core.config import settings
from .segmentation import Segmentation
from .enhancement import Enhancement


class ImageProcessor:
    """图像处理器 - 整合预处理、分离、增强功能"""
    
    def __init__(self, output_dir: str = "./processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.segmentation = Segmentation()
        self.enhancement = Enhancement()
    
    def load_image(self, image_path: str) -> np.ndarray:
        """加载图片
        
        训练/推理阶段优先读取本地文件；如果路径是后端 uploads 的相对路径（例如 ./uploads/... 或 /uploads/...），
        则通过 settings.BACKEND_ORIGIN 从后端 HTTP 拉取。
        """
        # 1) 本地绝对/相对路径存在则直接读取
        if os.path.exists(image_path):
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法读取图片: {image_path}")
            return image

        # 2) 处理后端上传目录相对路径：./uploads/... 或 uploads/... 或 /uploads/...
        normalized = image_path.strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized.startswith("uploads/"):
            normalized = "/" + normalized
        if normalized.startswith("/uploads/"):
            url = urljoin(settings.BACKEND_ORIGIN.rstrip("/") + "/", normalized.lstrip("/"))
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = resp.read()
                arr = np.frombuffer(data, dtype=np.uint8)
                image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if image is None:
                    raise ValueError(f"无法解码图片: {url}")
                return image
            except Exception as e:
                raise FileNotFoundError(f"图片文件不存在且HTTP拉取失败: path={image_path}, url={url}, err={e}")

        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    def crop_region(self, image: np.ndarray, bbox: Dict) -> np.ndarray:
        """裁剪指定区域"""
        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        width = bbox.get("width", image.shape[1])
        height = bbox.get("height", image.shape[0])
        
        # 确保坐标在图像范围内
        x = max(0, min(x, image.shape[1] - 1))
        y = max(0, min(y, image.shape[0] - 1))
        width = min(width, image.shape[1] - x)
        height = min(height, image.shape[0] - y)
        
        return image[y:y+height, x:x+width]
    
    def process_sample(
        self,
        image_path: str,
        separation_mode: str = "auto",
        annotation: Optional[Dict] = None,
        save_processed: bool = True
    ) -> Tuple[np.ndarray, Optional[str]]:
        """
        处理样本图片
        
        Args:
            image_path: 图片路径
            separation_mode: 分离模式 ("auto", "color", "texture", "edge", "none")
            annotation: 手动标注的区域信息 {"bbox": {"x": 10, "y": 20, "width": 100, "height": 50}}
            save_processed: 是否保存处理后的图片
        
        Returns:
            (processed_image, extracted_path)
        """
        # 加载图片
        image = self.load_image(image_path)
        
        # 提取手写区域
        handwriting_region = None
        extracted_path = None
        
        if annotation and "bbox" in annotation:
            # 使用手动标注的区域
            handwriting_region = self.crop_region(image, annotation["bbox"])
        elif separation_mode == "none":
            # 不分离，使用整张图片
            handwriting_region = image
        elif separation_mode == "auto":
            # 自动检测手写区域
            result = self.segmentation.auto_detect_handwriting_region(image)
            if result:
                handwriting_region = result["region"]
            else:
                # 如果自动检测失败，使用整张图片
                handwriting_region = image
        elif separation_mode == "color":
            _, handwriting_region = self.segmentation.separate_by_color(image)
        elif separation_mode == "texture":
            _, handwriting_region = self.segmentation.separate_by_texture(image)
        elif separation_mode == "edge":
            _, handwriting_region = self.segmentation.separate_by_edge(image)
        else:
            handwriting_region = image
        
        # 如果手写区域为空，使用整张图片
        if handwriting_region is None or handwriting_region.size == 0:
            handwriting_region = image
        
        # 图像增强
        enhanced = self.enhancement.enhance(handwriting_region)
        
        # 转换为RGB格式（用于模型输入）
        if len(enhanced.shape) == 2:
            # 灰度图转RGB
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        elif len(enhanced.shape) == 3 and enhanced.shape[2] == 3:
            # BGR转RGB
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        
        # 归一化到0-1范围
        processed_image = enhanced.astype(np.float32) / 255.0
        
        # 保存处理后的图片
        if save_processed:
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            extracted_path = os.path.join(self.output_dir, f"{name}_processed{ext}")
            
            # 保存为uint8格式
            save_image = (processed_image * 255).astype(np.uint8)
            # 转换回BGR用于保存
            if len(save_image.shape) == 3:
                save_image = cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(extracted_path, save_image)
        
        return processed_image, extracted_path
    
    def process_batch(
        self,
        image_paths: list,
        separation_mode: str = "auto",
        annotations: Optional[list] = None
    ) -> list:
        """批量处理图片"""
        results = []
        for i, image_path in enumerate(image_paths):
            annotation = annotations[i] if annotations and i < len(annotations) else None
            try:
                processed_image, extracted_path = self.process_sample(
                    image_path,
                    separation_mode=separation_mode,
                    annotation=annotation
                )
                results.append({
                    "image_path": image_path,
                    "processed_image": processed_image,
                    "extracted_path": extracted_path,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "image_path": image_path,
                    "processed_image": None,
                    "extracted_path": None,
                    "success": False,
                    "error": str(e)
                })
        return results
