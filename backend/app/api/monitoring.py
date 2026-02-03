"""
性能监控API端点
提供性能指标、日志查询和系统健康检查
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..middleware.performance import metrics_collector
from ..utils.structured_logger import get_structured_logger
from ..core.config import settings
import psutil
import os

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

logger = get_structured_logger(__name__, log_dir=settings.UPLOAD_DIR.replace('uploads', 'logs'))


@router.get("/metrics")
async def get_metrics(
    metric_name: Optional[str] = None,
    minutes: int = Query(5, ge=1, le=60),
    format_type: str = Query("summary", pattern="^(summary|raw)$")
):
    """
    获取性能指标

    Args:
        metric_name: 指标名称，如果为空则返回所有指标
        minutes: 时间范围（分钟）
        format_type: 返回格式（summary汇总或raw原始数据）

    Returns:
        性能指标数据
    """
    try:
        if metric_name:
            # 获取特定指标
            if format_type == "raw":
                metrics = metrics_collector.get_metrics(metric_name, minutes)
            else:
                # 返回汇总信息
                metrics = {
                    "metric_name": metric_name,
                    "time_range_minutes": minutes,
                    "count": len(metrics_collector.get_metrics(metric_name, minutes)),
                    "average": metrics_collector.get_average(metric_name, minutes),
                    "p95": metrics_collector.get_percentile(metric_name, 95, minutes),
                    "p99": metrics_collector.get_percentile(metric_name, 99, minutes)
                }
        else:
            # 获取所有关键指标的汇总
            key_metrics = [
                "http_request_duration_ms",
                "http_requests_total",
                "http_errors_total"
            ]

            metrics = {}
            for key_metric in key_metrics:
                raw_data = metrics_collector.get_metrics(key_metric, minutes)
                metrics[key_metric] = {
                    "count": len(raw_data),
                    "average": metrics_collector.get_average(key_metric, minutes),
                    "p95": metrics_collector.get_percentile(key_metric, 95, minutes),
                    "p99": metrics_collector.get_percentile(key_metric, 99, minutes)
                }

        return {
            "success": True,
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(detailed: bool = False):
    """
    系统健康检查

    Args:
        detailed: 是否返回详细信息

    Returns:
        健康状态信息
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

    if detailed:
        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # 检查磁盘使用
        disk = psutil.disk_usage(settings.UPLOAD_DIR)

        # 检查进程状态
        process = psutil.Process(os.getpid())

        health_status.update({
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "process": {
                    "pid": process.pid,
                    "memory_percent": process.memory_percent(),
                    "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                    "status": process.status()
                }
            }
        })

        # 检查各组件状态
        health_status["components"] = {
            "database": "unknown",  # TODO: 实现数据库连接检查
            "inference_service": "unknown",  # TODO: 实现推理服务连接检查
            "redis": "unknown"  # TODO: 实现Redis连接检查
        }

    return health_status


@router.get("/logs")
async def query_logs(
    level: Optional[str] = Query(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    keyword: Optional[str] = None
):
    """
    查询日志

    Args:
        level: 日志级别
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
        limit: 返回条数限制
        keyword: 关键词搜索

    Returns:
        日志记录列表
    """
    try:
        # 这里需要实现日志查询逻辑
        # 由于使用的是文件日志，需要读取并解析日志文件
        # 简化实现：返回最近的日志条目

        log_file = settings.UPLOAD_DIR.replace('uploads', 'logs') + "/backend.log"

        if not os.path.exists(log_file):
            return {
                "success": True,
                "data": [],
                "message": "日志文件不存在",
                "timestamp": datetime.utcnow().isoformat()
            }

        # 读取并过滤日志
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if len(logs) >= limit:
                    break

                # 简单的关键词过滤
                if keyword and keyword.lower() not in line.lower():
                    continue

                # 简单的级别过滤
                if level and level not in line:
                    continue

                logs.append(line.strip())

        return {
            "success": True,
            "data": logs,
            "count": len(logs),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"查询日志失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    获取系统统计信息

    Returns:
        系统统计数据
    """
    try:
        from ..models.user import User
        from ..models.sample import Sample
        from ..models.recognition_log import RecognitionLog
        from ..models.training_job import TrainingJob

        # 统计用户数量
        total_users = db.query(User).count()

        # 统计样本数量
        total_samples = db.query(Sample).count()

        # 统计识别次数
        total_recognitions = db.query(RecognitionLog).count()

        # 统计训练任务数量
        total_trainings = db.query(TrainingJob).count()

        # 统计最近24小时的识别次数
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_recognitions = db.query(RecognitionLog).filter(
            RecognitionLog.created_at >= yesterday
        ).count()

        return {
            "success": True,
            "data": {
                "users": {
                    "total": total_users
                },
                "samples": {
                    "total": total_samples
                },
                "recognition": {
                    "total": total_recognitions,
                    "recent_24h": recent_recognitions
                },
                "training": {
                    "total": total_trainings
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-old-metrics")
async def clear_old_metrics(hours: int = Query(24, ge=1, le=168)):
    """
    清理旧的性能指标数据

    Args:
        hours: 清理多少小时之前的数据

    Returns:
        操作结果
    """
    try:
        metrics_collector.clear_old_metrics(hours)

        logger.info(f"已清理{hours}小时前的性能指标数据")

        return {
            "success": True,
            "message": f"已清理{hours}小时前的性能指标数据",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"清理性能指标失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
