import torch
import torch.nn as nn
import torchvision.models as models
from typing import Tuple
import os


class SiameseNetwork(nn.Module):
    """Siamese Network for handwriting recognition"""
    
    def __init__(self, embedding_dim: int = 512):
        super(SiameseNetwork, self).__init__()
        resnet = models.resnet18(pretrained=True)
        self.feature_extractor = nn.Sequential(*list(resnet.children())[:-1])
        self.fc = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, embedding_dim)
        )
    
    def forward_one(self, x):
        """提取单张图片的特征"""
        x = self.feature_extractor(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = nn.functional.normalize(x, p=2, dim=1)
        return x
    
    def forward(self, input1, input2=None):
        """前向传播"""
        if input2 is None:
            return self.forward_one(input1)
        else:
            output1 = self.forward_one(input1)
            output2 = self.forward_one(input2)
            return output1, output2


class ModelManager:
    """模型管理器"""
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.current_version = None
        os.makedirs(model_dir, exist_ok=True)
    
    def load_model(self, version: str = "latest") -> SiameseNetwork:
        """加载模型"""
        if version == "latest":
            model_files = [f for f in os.listdir(self.model_dir) if f.endswith(".pth")]
            if not model_files:
                self.model = SiameseNetwork()
                self.current_version = "initial"
                return self.model
            version = sorted(model_files)[-1].replace(".pth", "")
        
        model_path = os.path.join(self.model_dir, f"{version}.pth")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self.model = SiameseNetwork()
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        self.current_version = version
        return self.model
    
    def save_model(self, model: SiameseNetwork, version: str):
        """保存模型"""
        model_path = os.path.join(self.model_dir, f"{version}.pth")
        torch.save(model.state_dict(), model_path)
        self.current_version = version
    
    def extract_features(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """提取图片特征"""
        if self.model is None:
            self.load_model()
        
        with torch.no_grad():
            image_tensor = image_tensor.to(self.device)
            if len(image_tensor.shape) == 3:
                image_tensor = image_tensor.unsqueeze(0)
            features = self.model.forward_one(image_tensor)
        return features.cpu()
