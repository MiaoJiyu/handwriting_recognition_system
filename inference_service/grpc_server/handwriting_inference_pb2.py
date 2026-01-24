# -*- coding: utf-8 -*-
# Generated protocol buffer code (placeholder)
# This is a minimal implementation to allow the server to run
# For production, generate proper code using: python generate_proto.py

class RecognitionResult(object):
    """识别结果"""
    def __init__(self, user_id=0, username="", score=0.0):
        self.user_id = user_id
        self.username = username
        self.score = score

class RecognizeRequest(object):
    """识别请求"""
    def __init__(self, image_path=None, image_data=None, top_k=5):
        self.image_path = image_path
        self.image_data = image_data
        self.top_k = top_k

class RecognizeResponse(object):
    """识别响应"""
    def __init__(self):
        self.top_k = []
        self.is_unknown = False
        self.confidence = 0.0
        self.error_message = ""

class BatchRecognizeRequest(object):
    """批量识别请求"""
    def __init__(self):
        self.image_paths = []
        self.image_data = []
        self.top_k = 5

class BatchRecognizeResponse(object):
    """批量识别响应"""
    def __init__(self):
        self.results = []
        self.error_message = ""

class TrainRequest(object):
    """训练请求"""
    def __init__(self, job_id=0, force_retrain=False):
        self.job_id = job_id
        self.force_retrain = force_retrain

class TrainResponse(object):
    """训练响应"""
    def __init__(self, success=False, message="", job_id=0):
        self.success = success
        self.message = message
        self.job_id = job_id

class TrainingStatusRequest(object):
    """训练状态请求"""
    def __init__(self, job_id=0):
        self.job_id = job_id

class TrainingStatusResponse(object):
    """训练状态响应"""
    def __init__(self):
        self.status = "pending"
        self.progress = 0.0
        self.model_version_id = 0
        self.error_message = ""

class ConfigUpdateRequest(object):
    """配置更新请求"""
    def __init__(self):
        self.similarity_threshold = 0.0
        self.gap_threshold = 0.0
        self.top_k = 0

class ConfigResponse(object):
    """配置响应"""
    def __init__(self, success=False, message=""):
        self.success = success
        self.message = message
