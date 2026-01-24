"""
共享类型定义

此模块定义了系统中各组件共享的数据类型和结构。
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# =====================================================
# 用户相关类型
# =====================================================

class UserRole(str, Enum):
    """用户角色枚举"""
    SYSTEM_ADMIN = "system_admin"  # 系统管理员
    SCHOOL_ADMIN = "school_admin"  # 学校管理员
    TEACHER = "teacher"            # 教师
    STUDENT = "student"            # 学生


@dataclass
class UserInfo:
    """用户信息"""
    id: int
    username: str
    role: UserRole
    school_id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role in [UserRole.SYSTEM_ADMIN, UserRole.SCHOOL_ADMIN]
    
    def is_teacher_or_above(self) -> bool:
        """是否为教师或更高权限"""
        return self.role in [UserRole.SYSTEM_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER]


# =====================================================
# 样本相关类型
# =====================================================

class SampleStatus(str, Enum):
    """样本状态枚举"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    PROCESSED = "processed"    # 已处理
    FAILED = "failed"          # 处理失败


@dataclass
class BoundingBox:
    """边界框"""
    x: int
    y: int
    width: int
    height: int
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'BoundingBox':
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"]
        )


@dataclass
class SampleRegion:
    """样本区域"""
    id: int
    sample_id: int
    bbox: BoundingBox
    is_auto_detected: bool
    created_at: Optional[datetime] = None


@dataclass
class Sample:
    """样本信息"""
    id: int
    user_id: int
    image_path: str
    original_filename: str
    status: SampleStatus
    extracted_region_path: Optional[str] = None
    sample_metadata: Optional[Dict[str, Any]] = None
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    regions: List[SampleRegion] = field(default_factory=list)


# =====================================================
# 识别相关类型
# =====================================================

@dataclass
class RecognitionResult:
    """单个识别结果"""
    user_id: int
    username: str
    score: float  # 相似度分数 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "score": self.score
        }


@dataclass
class RecognitionResponse:
    """识别响应"""
    top_k: List[RecognitionResult]
    is_unknown: bool
    confidence: float
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_k": [r.to_dict() for r in self.top_k],
            "is_unknown": self.is_unknown,
            "confidence": self.confidence,
            "error_message": self.error_message
        }


# =====================================================
# 训练相关类型
# =====================================================

class TrainingStatus(str, Enum):
    """训练状态枚举"""
    PENDING = "pending"      # 待开始
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


@dataclass
class TrainingJob:
    """训练任务"""
    id: int
    status: TrainingStatus
    progress: float  # 0.0 - 1.0
    model_version_id: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =====================================================
# 特征相关类型
# =====================================================

@dataclass
class FeatureVector:
    """特征向量"""
    user_id: int
    vector: List[float]
    sample_ids: List[int]
    updated_at: Optional[datetime] = None
    
    @property
    def dimension(self) -> int:
        """特征维度"""
        return len(self.vector)


# =====================================================
# API响应类型
# =====================================================

@dataclass
class APIResponse:
    """通用API响应"""
    success: bool
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class PaginatedResponse:
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """总页数"""
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1
