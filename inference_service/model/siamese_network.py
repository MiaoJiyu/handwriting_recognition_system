import os
import torch
import torch.nn as nn
import torchvision.models as models


class SiameseNetwork(nn.Module):
    """Siamese Network for handwriting recognition"""

    def __init__(self, embedding_dim: int = 512, use_imagenet_pretrained: bool = True):
        super(SiameseNetwork, self).__init__()

        # 兼容 torchvision 新旧版本的 pretrained/weights API。
        # 用户选择了“无 .pth 时尝试使用 ImageNet 预训练”，因此默认 use_imagenet_pretrained=True。
        if use_imagenet_pretrained:
            try:
                weights = models.ResNet18_Weights.DEFAULT
                resnet = models.resnet18(weights=weights)
            except Exception:
                resnet = models.resnet18(pretrained=True)
        else:
            try:
                resnet = models.resnet18(weights=None)
            except Exception:
                resnet = models.resnet18(pretrained=False)

        self.feature_extractor = nn.Sequential(*list(resnet.children())[:-1])
        self.fc = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, embedding_dim),
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

    def __init__(self, model_dir: str = "./models", device: str | None = None, use_imagenet_pretrained: bool = True):
        self.model_dir = model_dir
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        self.use_imagenet_pretrained = use_imagenet_pretrained
        self.model = None
        self.current_version = None
        os.makedirs(model_dir, exist_ok=True)

    def load_model(self, version: str = "latest") -> SiameseNetwork:
        """加载模型

        - version=latest：优先加载 model_dir 下最新的 .pth；若不存在则回退到 ImageNet 预训练（按 use_imagenet_pretrained）。
        """
        resolved_version = version
        if version == "latest":
            model_files = [f for f in os.listdir(self.model_dir) if f.endswith(".pth")]
            if model_files:
                resolved_version = sorted(model_files)[-1].replace(".pth", "")
            else:
                resolved_version = "initial"

        if resolved_version == "initial":
            self.model = SiameseNetwork(use_imagenet_pretrained=self.use_imagenet_pretrained)
            self.model.to(self.device)
            self.model.eval()
            self.current_version = "initial"
            return self.model

        model_path = os.path.join(self.model_dir, f"{resolved_version}.pth")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        self.model = SiameseNetwork(use_imagenet_pretrained=self.use_imagenet_pretrained)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        self.current_version = resolved_version
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
