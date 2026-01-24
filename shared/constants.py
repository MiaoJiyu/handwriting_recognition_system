"""
共享常量定义

此模块定义了系统中各组件共享的常量值。
"""

# =====================================================
# 系统版本信息
# =====================================================
SYSTEM_NAME = "字迹识别系统"
SYSTEM_VERSION = "1.0.0"
API_VERSION = "v1"

# =====================================================
# 默认配置值
# =====================================================

# 数据库相关
DEFAULT_DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/handwriting_recognition?charset=utf8mb4"

# Redis相关
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0

# JWT相关
DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"
DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# gRPC相关
DEFAULT_GRPC_HOST = "0.0.0.0"
DEFAULT_GRPC_PORT = 50051

# =====================================================
# 文件存储相关
# =====================================================
DEFAULT_UPLOAD_DIR = "./uploads"
DEFAULT_SAMPLES_DIR = "./uploads/samples"
DEFAULT_MODELS_DIR = "./models"

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff"
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# =====================================================
# 特征提取相关
# =====================================================

# 深度学习特征维度
DEEP_FEATURE_DIMENSION = 512

# 传统特征维度
TRADITIONAL_FEATURE_DIMENSION = 128

# 融合后特征维度
FUSED_FEATURE_DIMENSION = 256

# 图像预处理尺寸
IMAGE_INPUT_SIZE = (224, 224)
IMAGE_RESIZE_SIZE = (256, 256)

# =====================================================
# 匹配算法相关
# =====================================================

# 相似度阈值（低于此值判定为未知）
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# 最高与次高差距阈值（低于此值判定为未知）
DEFAULT_GAP_THRESHOLD = 0.1

# Top-K默认值
DEFAULT_TOP_K = 5

# 未知判断相关
MIN_CONFIDENCE_FOR_KNOWN = 0.75
MAX_CANDIDATES_FOR_UNKNOWN = 3

# =====================================================
# 训练相关
# =====================================================

# 默认训练参数
DEFAULT_BATCH_SIZE = 32
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_NUM_EPOCHS = 100
DEFAULT_EARLY_STOPPING_PATIENCE = 10

# 数据增强参数
AUGMENTATION_ROTATION_RANGE = 15  # 旋转角度范围
AUGMENTATION_SCALE_RANGE = (0.9, 1.1)  # 缩放范围
AUGMENTATION_NOISE_FACTOR = 0.05  # 噪声因子

# =====================================================
# 用户权限相关
# =====================================================

# 角色权限映射
ROLE_PERMISSIONS = {
    "system_admin": [
        "manage_users",
        "manage_schools",
        "manage_samples",
        "manage_training",
        "view_all_logs",
        "system_config"
    ],
    "school_admin": [
        "manage_school_users",
        "manage_samples",
        "manage_training",
        "view_school_logs"
    ],
    "teacher": [
        "manage_samples",
        "recognize_samples",
        "view_student_samples"
    ],
    "student": [
        "upload_samples",
        "view_own_samples"
    ]
}

# 需要管理员权限的操作
ADMIN_ONLY_OPERATIONS = [
    "delete_user",
    "change_user_role",
    "start_training",
    "delete_model"
]

# =====================================================
# API相关
# =====================================================

# 分页默认值
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# API限流（每分钟请求数）
RATE_LIMIT_PER_MINUTE = 60
RECOGNITION_RATE_LIMIT_PER_MINUTE = 20

# 请求超时（秒）
DEFAULT_REQUEST_TIMEOUT = 30
RECOGNITION_REQUEST_TIMEOUT = 60
TRAINING_REQUEST_TIMEOUT = 3600

# =====================================================
# 错误码定义
# =====================================================

class ErrorCode:
    """错误码定义"""
    # 通用错误 1xxx
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    
    # 认证错误 2xxx
    INVALID_CREDENTIALS = 2001
    TOKEN_EXPIRED = 2002
    TOKEN_INVALID = 2003
    
    # 用户错误 3xxx
    USER_NOT_FOUND = 3001
    USER_ALREADY_EXISTS = 3002
    INVALID_ROLE = 3003
    
    # 样本错误 4xxx
    SAMPLE_NOT_FOUND = 4001
    INVALID_IMAGE_FORMAT = 4002
    FILE_TOO_LARGE = 4003
    UPLOAD_FAILED = 4004
    
    # 识别错误 5xxx
    RECOGNITION_FAILED = 5001
    NO_FEATURES_AVAILABLE = 5002
    MODEL_NOT_LOADED = 5003
    
    # 训练错误 6xxx
    TRAINING_ALREADY_RUNNING = 6001
    TRAINING_FAILED = 6002
    INSUFFICIENT_SAMPLES = 6003


# 错误消息映射
ERROR_MESSAGES = {
    ErrorCode.UNKNOWN_ERROR: "未知错误",
    ErrorCode.INVALID_REQUEST: "无效的请求",
    ErrorCode.UNAUTHORIZED: "未授权",
    ErrorCode.FORBIDDEN: "禁止访问",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ErrorCode.TOKEN_EXPIRED: "Token已过期",
    ErrorCode.TOKEN_INVALID: "无效的Token",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.USER_ALREADY_EXISTS: "用户名已存在",
    ErrorCode.INVALID_ROLE: "无效的角色",
    ErrorCode.SAMPLE_NOT_FOUND: "样本不存在",
    ErrorCode.INVALID_IMAGE_FORMAT: "无效的图片格式",
    ErrorCode.FILE_TOO_LARGE: "文件过大",
    ErrorCode.UPLOAD_FAILED: "上传失败",
    ErrorCode.RECOGNITION_FAILED: "识别失败",
    ErrorCode.NO_FEATURES_AVAILABLE: "没有可用的特征数据",
    ErrorCode.MODEL_NOT_LOADED: "模型未加载",
    ErrorCode.TRAINING_ALREADY_RUNNING: "训练任务正在运行中",
    ErrorCode.TRAINING_FAILED: "训练失败",
    ErrorCode.INSUFFICIENT_SAMPLES: "样本数量不足",
}
