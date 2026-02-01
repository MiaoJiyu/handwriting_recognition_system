"""
Task Scheduler Service using APScheduler

This service manages scheduled training tasks with support for:
- One-time execution
- Interval-based execution
- Cron-based execution
- Full and incremental training modes
- School-specific training
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.scheduled_task import ScheduledTask, ScheduledTaskExecution, ScheduleStatus, ScheduleTriggerType
from ..models.training_job import TrainingJob, TrainingJobStatus
from ..models.user import User
from ..models.school import School

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        """初始化调度器"""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,  # 每个任务最多同时运行1个实例
            'misfire_grace_time': 300  # 错过执行时间后300秒内仍可执行
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

    async def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            logger.info("Task scheduler started successfully")
            # 加载数据库中的激活任务
            await self.load_active_tasks()
        except Exception as e:
            logger.error(f"Failed to start task scheduler: {e}")
            raise

    async def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Task scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop task scheduler: {e}")
            raise

    async def load_active_tasks(self):
        """从数据库加载激活的任务"""
        db = SessionLocal()
        try:
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status == ScheduleStatus.ACTIVE
            ).all()

            for task in tasks:
                try:
                    await self.schedule_task(task.id, db=db)
                except Exception as e:
                    logger.error(f"Failed to load task {task.id}: {e}")

            logger.info(f"Loaded {len(tasks)} active tasks")
        finally:
            db.close()

    async def schedule_task(self, task_id: int, db: Optional[Session] = None) -> bool:
        """调度任务"""
        should_close_db = db is None
        if should_close_db:
            db = SessionLocal()

        try:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            # 如果任务已存在，先移除
            job_id = f"scheduled_task_{task.id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # 根据触发器类型创建触发器
            if task.trigger_type == ScheduleTriggerType.ONCE:
                if not task.run_at:
                    logger.error(f"Task {task_id} has no run_at time")
                    return False

                trigger = DateTrigger(
                    run_date=task.run_at,
                    timezone='UTC'
                )

            elif task.trigger_type == ScheduleTriggerType.INTERVAL:
                if not task.interval_seconds or task.interval_seconds <= 0:
                    logger.error(f"Task {task_id} has invalid interval")
                    return False

                trigger = IntervalTrigger(
                    seconds=task.interval_seconds,
                    timezone='UTC'
                )

            elif task.trigger_type == ScheduleTriggerType.CRON:
                if not task.cron_expression:
                    logger.error(f"Task {task_id} has no cron expression")
                    return False

                # 解析cron表达式 (简化版: 分 时 日 月 周)
                parts = task.cron_expression.split()
                if len(parts) != 5:
                    logger.error(f"Invalid cron expression: {task.cron_expression}")
                    return False

                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone='UTC'
                )

            else:
                logger.error(f"Unknown trigger type: {task.trigger_type}")
                return False

            # 添加任务到调度器
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                id=job_id,
                args=[task.id],
                name=f"{task.name} (ID: {task.id})",
                replace_existing=True
            )

            # 更新下次执行时间
            job = self.scheduler.get_job(job_id)
            if job:
                task.next_run_at = job.next_run_time
                db.commit()

            logger.info(f"Scheduled task {task.id} ({task.name}) with trigger type {task.trigger_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule task {task_id}: {e}")
            return False
        finally:
            if should_close_db:
                db.close()

    async def unschedule_task(self, task_id: int) -> bool:
        """取消任务调度"""
        try:
            job_id = f"scheduled_task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Unscheduled task {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unschedule task {task_id}: {e}")
            return False

    async def pause_task(self, task_id: int, db: Session) -> bool:
        """暂停任务"""
        try:
            # 取消调度
            await self.unschedule_task(task_id)

            # 更新数据库状态
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.status = ScheduleStatus.PAUSED
                db.commit()

            logger.info(f"Paused task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False

    async def resume_task(self, task_id: int, db: Session) -> bool:
        """恢复任务"""
        try:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if not task:
                return False

            task.status = ScheduleStatus.ACTIVE
            db.commit()

            # 重新调度
            return await self.schedule_task(task_id, db=db)
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False

    async def _execute_task(self, task_id: int):
        """执行任务（由调度器调用）"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if not task or task.status != ScheduleStatus.ACTIVE:
                logger.warning(f"Task {task_id} not found or not active")
                return

            # 创建执行记录
            execution = ScheduledTaskExecution(
                scheduled_task_id=task.id,
                status="running"
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

            logger.info(f"Executing task {task_id} ({task.name})")

            # 创建训练任务
            training_job = TrainingJob(
                status=TrainingJobStatus.PENDING,
                progress=0.0,
                scheduled_task_id=task.id
            )
            db.add(training_job)
            db.commit()
            db.refresh(training_job)

            # 关联执行记录和训练任务
            execution.training_job_id = training_job.id
            db.commit()

            # 根据训练模式执行训练
            if task.training_mode == "full":
                await self._execute_full_training(task, training_job, db)
            elif task.training_mode == "incremental":
                await self._execute_incremental_training(task, training_job, db)
            else:
                raise ValueError(f"Unknown training mode: {task.training_mode}")

            # 更新执行记录
            execution.status = training_job.status.value
            execution.completed_at = datetime.now(timezone.utc)
            if training_job.error_message:
                execution.error_message = training_job.error_message

            # 更新任务统计
            task.last_run_at = execution.completed_at
            task.total_runs += 1
            if training_job.status == TrainingJobStatus.COMPLETED:
                task.success_runs += 1
                task.last_error = None
            else:
                task.failed_runs += 1
                task.last_error = training_job.error_message

            db.commit()

            # 更新下次执行时间
            job_id = f"scheduled_task_{task.id}"
            job = self.scheduler.get_job(job_id)
            if job:
                task.next_run_at = job.next_run_time
                db.commit()

            logger.info(f"Task {task_id} execution completed: {training_job.status.value}")

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")

            # 更新执行记录
            if 'execution' in locals():
                execution.status = "failed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = str(e)

                # 更新任务统计
                if 'task' in locals():
                    task.failed_runs += 1
                    task.last_error = str(e)

                db.commit()

        finally:
            db.close()

    async def _execute_full_training(self, task: ScheduledTask, training_job: TrainingJob, db: Session):
        """执行全量训练"""
        from ..services.inference_client import InferenceClient

        try:
            # 检查样本数量
            from ..models.sample import Sample, SampleStatus
            query = db.query(Sample).filter(Sample.status == SampleStatus.PROCESSED)

            # 如果指定了学校，只训练该学校的数据
            if task.school_id:
                from ..models.user import User
                user_ids = db.query(User.id).filter(User.school_id == task.school_id).all()
                user_ids = [uid[0] for uid in user_ids]
                query = query.filter(Sample.user_id.in_(user_ids))

            eligible_samples = query.count()
            if eligible_samples < 3:
                raise Exception(f"样本数量不足，至少需要3个已处理(PROCESSED)的样本，当前={eligible_samples}")

            # 调用推理服务进行训练
            client = InferenceClient()
            await client.train_model(
                training_job.id,
                force_retrain=task.force_retrain,
                school_id=task.school_id
            )

            # 更新训练任务状态
            training_job.status = TrainingJobStatus.RUNNING
            training_job.started_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Full training started for task {task.id}")

        except Exception as e:
            training_job.status = TrainingJobStatus.FAILED
            training_job.error_message = str(e)
            training_job.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

    async def _execute_incremental_training(self, task: ScheduledTask, training_job: TrainingJob, db: Session):
        """执行增量训练"""
        from ..services.inference_client import InferenceClient

        try:
            # 检查是否有新增样本
            from ..models.sample import Sample, SampleStatus
            from ..models.model import Model

            # 获取最新模型版本
            latest_model = db.query(Model).filter(Model.is_active == True).order_by(Model.created_at.desc()).first()

            query = db.query(Sample).filter(Sample.status == SampleStatus.PROCESSED)

            # 如果指定了学校，只训练该学校的数据
            if task.school_id:
                from ..models.user import User
                user_ids = db.query(User.id).filter(User.school_id == task.school_id).all()
                user_ids = [uid[0] for uid in user_ids]
                query = query.filter(Sample.user_id.in_(user_ids))

            # 如果有最新模型，只训练模型创建后的样本
            if latest_model:
                query = query.filter(Sample.created_at > latest_model.created_at)

            new_samples = query.count()

            if new_samples < 1:
                raise Exception(f"没有新增样本需要训练，当前={new_samples}")

            # 调用推理服务进行增量训练
            client = InferenceClient()
            await client.train_model(
                training_job.id,
                force_retrain=True,  # 增量训练需要强制重新训练
                school_id=task.school_id,
                incremental=True  # 标记为增量训练
            )

            # 更新训练任务状态
            training_job.status = TrainingJobStatus.RUNNING
            training_job.started_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Incremental training started for task {task.id} with {new_samples} new samples")

        except Exception as e:
            training_job.status = TrainingJobStatus.FAILED
            training_job.error_message = str(e)
            training_job.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

    def get_jobs_info(self) -> list[Dict[str, Any]]:
        """获取所有调度任务的信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


# 全局调度器实例
task_scheduler = TaskScheduler()
