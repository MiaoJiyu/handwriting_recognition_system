#!/usr/bin/env python3
"""
CLI工具 - 定时任务管理

使用方法:
    python scripts/cli/scheduled_tasks.py list                    # 列出所有定时任务
    python scripts/cli/scheduled_tasks.py create --name "任务名称" --trigger-type interval --interval 3600
    python scripts/cli/scheduled_tasks.py update --id 1 --name "新名称"
    python scripts/cli/scheduled_tasks.py pause --id 1
    python scripts/cli/scheduled_tasks.py resume --id 1
    python scripts/cli/scheduled_tasks.py delete --id 1
    python scripts/cli/scheduled_tasks.py history --id 1          # 查看任务执行历史
"""
import sys
import os
import argparse
from datetime import datetime, timezone
from typing import Optional

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.scheduled_task import (
    ScheduledTask, ScheduledTaskExecution,
    ScheduleStatus, ScheduleTriggerType
)
from app.models.user import User
from app.models.school import School


class ScheduledTasksCLI:
    """定时任务命令行工具"""

    def __init__(self):
        self.db = SessionLocal()

    def list_tasks(self, status: Optional[str] = None, training_mode: Optional[str] = None):
        """列出所有定时任务"""
        query = self.db.query(ScheduledTask)

        if status:
            query = query.filter(ScheduledTask.status == status)
        if training_mode:
            query = query.filter(ScheduledTask.training_mode == training_mode)

        tasks = query.order_by(ScheduledTask.created_at.desc()).all()

        if not tasks:
            print("未找到定时任务")
            return

        print("\n" + "=" * 150)
        print(f"{'ID':<5} {'名称':<20} {'状态':<10} {'触发方式':<25} {'训练模式':<10} {'学校':<15} {'执行次数':<15} {'下次执行':<20}")
        print("=" * 150)

        for task in tasks:
            # 获取触发器描述
            trigger_desc = ""
            if task.trigger_type == ScheduleTriggerType.ONCE:
                trigger_desc = f"一次性: {task.run_at.strftime('%Y-%m-%d %H:%M:%S') if task.run_at else '未设置'}"
            elif task.trigger_type == ScheduleTriggerType.INTERVAL:
                trigger_desc = f"间隔: {task.interval_seconds}秒"
            elif task.trigger_type == ScheduleTriggerType.CRON:
                trigger_desc = f"Cron: {task.cron_expression}"

            # 获取学校名称
            school_name = task.school.name if task.school else "全校"

            # 获取下次执行时间
            next_run = task.next_run_at.strftime('%Y-%m-%d %H:%M:%S') if task.next_run_at else "未设置"

            print(
                f"{task.id:<5} {task.name[:19]:<20} {task.status.value:<10} "
                f"{trigger_desc[:24]:<25} {task.training_mode:<10} {school_name:<15} "
                f"{f'{task.success_runs}/{task.total_runs}':<15} {next_run:<20}"
            )

        print("=" * 150)
        print(f"共 {len(tasks)} 个任务\n")

    def create_task(
        self,
        name: str,
        trigger_type: str,
        description: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        run_at: Optional[str] = None,
        training_mode: str = "full",
        school_id: Optional[int] = None,
        force_retrain: bool = False,
        created_by: int = 1  # 默认创建者ID
    ):
        """创建定时任务"""
        # 验证触发器配置
        if trigger_type == "once" and not run_at:
            print("错误: 一次性触发器需要指定 run_at 参数")
            return

        if trigger_type == "interval" and not interval_seconds:
            print("错误: 间隔触发器需要指定 interval_seconds 参数")
            return

        if trigger_type == "cron" and not cron_expression:
            print("错误: Cron触发器需要指定 cron_expression 参数")
            return

        # 验证学校是否存在
        if school_id:
            school = self.db.query(School).filter(School.id == school_id).first()
            if not school:
                print(f"错误: 学校 {school_id} 不存在")
                return

        # 验证创建者是否存在
        creator = self.db.query(User).filter(User.id == created_by).first()
        if not creator:
            print(f"错误: 用户 {created_by} 不存在")
            return

        # 解析运行时间
        parsed_run_at = None
        if run_at:
            try:
                parsed_run_at = datetime.fromisoformat(run_at)
                if parsed_run_at.tzinfo is None:
                    parsed_run_at = parsed_run_at.replace(tzinfo=timezone.utc)
            except ValueError:
                print("错误: run_at 格式错误，请使用 ISO 格式 (例如: 2024-01-01T00:00:00)")
                return

        # 创建任务
        task = ScheduledTask(
            name=name,
            description=description,
            status=ScheduleStatus.ACTIVE,
            trigger_type=ScheduleTriggerType(trigger_type),
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            run_at=parsed_run_at,
            training_mode=training_mode,
            school_id=school_id,
            force_retrain=force_retrain,
            created_by=created_by
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        print(f"定时任务创建成功！")
        print(f"任务ID: {task.id}")
        print(f"任务名称: {task.name}")
        print(f"触发方式: {trigger_type}")
        print(f"训练模式: {training_mode}")
        print(f"学校: {task.school.name if task.school else '全校'}")

    def update_task(
        self,
        task_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        trigger_type: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        run_at: Optional[str] = None,
        training_mode: Optional[str] = None,
        school_id: Optional[int] = None,
        force_retrain: Optional[bool] = None
    ):
        """更新定时任务"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        # 验证学校是否存在
        if school_id is not None:
            if school_id == 0:
                task.school_id = None
            else:
                school = self.db.query(School).filter(School.id == school_id).first()
                if not school:
                    print(f"错误: 学校 {school_id} 不存在")
                    return
                task.school_id = school_id

        # 解析运行时间
        parsed_run_at = None
        if run_at is not None:
            try:
                parsed_run_at = datetime.fromisoformat(run_at)
                if parsed_run_at.tzinfo is None:
                    parsed_run_at = parsed_run_at.replace(tzinfo=timezone.utc)
            except ValueError:
                print("错误: run_at 格式错误，请使用 ISO 格式 (例如: 2024-01-01T00:00:00)")
                return

        # 更新字段
        if name is not None:
            task.name = name
        if description is not None:
            task.description = description
        if status is not None:
            task.status = ScheduleStatus(status)
        if trigger_type is not None:
            task.trigger_type = ScheduleTriggerType(trigger_type)
        if interval_seconds is not None:
            task.interval_seconds = interval_seconds
        if cron_expression is not None:
            task.cron_expression = cron_expression
        if parsed_run_at is not None:
            task.run_at = parsed_run_at
        if training_mode is not None:
            task.training_mode = training_mode
        if force_retrain is not None:
            task.force_retrain = force_retrain

        self.db.commit()
        self.db.refresh(task)

        print(f"定时任务 {task_id} 更新成功！")

    def delete_task(self, task_id: int):
        """删除定时任务"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        self.db.delete(task)
        self.db.commit()

        print(f"定时任务 {task_id} 删除成功！")

    def pause_task(self, task_id: int):
        """暂停定时任务"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        task.status = ScheduleStatus.PAUSED
        self.db.commit()

        print(f"定时任务 {task_id} 已暂停！")
        print("注意: 需要重启后端服务才能停止调度器中的任务")

    def resume_task(self, task_id: int):
        """恢复定时任务"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        task.status = ScheduleStatus.ACTIVE
        self.db.commit()

        print(f"定时任务 {task_id} 已恢复！")
        print("注意: 需要重启后端服务才能重新调度任务")

    def show_history(self, task_id: int, limit: int = 20):
        """查看任务执行历史"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        executions = self.db.query(ScheduledTaskExecution).filter(
            ScheduledTaskExecution.scheduled_task_id == task_id
        ).order_by(ScheduledTaskExecution.started_at.desc()).limit(limit).all()

        print(f"\n任务: {task.name} (ID: {task.id})")
        print("执行历史:\n")

        if not executions:
            print("暂无执行记录\n")
            return

        print("-" * 120)
        print(f"{'执行ID':<10} {'状态':<12} {'开始时间':<25} {'完成时间':<25} {'训练任务ID':<15} {'错误信息':<30}")
        print("-" * 120)

        for exec in executions:
            started_at = exec.started_at.strftime('%Y-%m-%d %H:%M:%S')
            completed_at = exec.completed_at.strftime('%Y-%m-%d %H:%M:%S') if exec.completed_at else "未完成"
            error_msg = exec.error_message[:29] if exec.error_message else ""

            print(
                f"{exec.id:<10} {exec.status:<12} {started_at:<25} "
                f"{completed_at:<25} {str(exec.training_job_id or ''):<15} {error_msg:<30}"
            )

        print("-" * 120)
        print(f"共 {len(executions)} 条执行记录\n")

    def show_task(self, task_id: int):
        """显示任务详情"""
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            print(f"错误: 任务 {task_id} 不存在")
            return

        print("\n" + "=" * 80)
        print(f"任务ID: {task.id}")
        print(f"任务名称: {task.name}")
        print(f"描述: {task.description or '无'}")
        print(f"状态: {task.status.value}")
        print(f"触发方式: {task.trigger_type.value}")
        print(f"训练模式: {task.training_mode}")
        print(f"学校: {task.school.name if task.school else '全校'}")
        print(f"强制重新训练: {'是' if task.force_retrain else '否'}")

        print("\n触发器配置:")
        if task.trigger_type == ScheduleTriggerType.ONCE:
            print(f"  执行时间: {task.run_at.strftime('%Y-%m-%d %H:%M:%S') if task.run_at else '未设置'}")
        elif task.trigger_type == ScheduleTriggerType.INTERVAL:
            print(f"  间隔秒数: {task.interval_seconds}")
        elif task.trigger_type == ScheduleTriggerType.CRON:
            print(f"  Cron表达式: {task.cron_expression}")

        print("\n执行统计:")
        print(f"  总执行次数: {task.total_runs}")
        print(f"  成功次数: {task.success_runs}")
        print(f"  失败次数: {task.failed_runs}")
        print(f"  最后执行时间: {task.last_run_at.strftime('%Y-%m-%d %H:%M:%S') if task.last_run_at else '未执行'}")
        print(f"  下次执行时间: {task.next_run_at.strftime('%Y-%m-%d %H:%M:%S') if task.next_run_at else '未设置'}")

        if task.last_error:
            print(f"  最后错误: {task.last_error}")

        print(f"\n创建者: {task.creator.nickname or task.creator.username if task.creator else '未知'}")
        print(f"创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"更新时间: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def close(self):
        """关闭数据库连接"""
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description='定时任务管理CLI工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # List命令
    list_parser = subparsers.add_parser('list', help='列出所有定时任务')
    list_parser.add_argument('--status', help='按状态筛选 (active/paused/completed/failed)')
    list_parser.add_argument('--training-mode', help='按训练模式筛选 (full/incremental)')

    # Create命令
    create_parser = subparsers.add_parser('create', help='创建定时任务')
    create_parser.add_argument('--name', required=True, help='任务名称')
    create_parser.add_argument('--description', help='任务描述')
    create_parser.add_argument('--trigger-type', required=True, choices=['once', 'interval', 'cron'], help='触发方式')
    create_parser.add_argument('--interval', type=int, help='间隔秒数 (interval触发器)')
    create_parser.add_argument('--cron', help='Cron表达式 (cron触发器)')
    create_parser.add_argument('--run-at', help='执行时间 ISO格式 (once触发器)')
    create_parser.add_argument('--training-mode', default='full', choices=['full', 'incremental'], help='训练模式')
    create_parser.add_argument('--school-id', type=int, help='学校ID (可选，为空表示全校)')
    create_parser.add_argument('--force-retrain', action='store_true', help='是否强制重新训练')
    create_parser.add_argument('--created-by', type=int, default=1, help='创建者用户ID')

    # Update命令
    update_parser = subparsers.add_parser('update', help='更新定时任务')
    update_parser.add_argument('--id', required=True, type=int, help='任务ID')
    update_parser.add_argument('--name', help='任务名称')
    update_parser.add_argument('--description', help='任务描述')
    update_parser.add_argument('--status', choices=['active', 'paused', 'completed', 'failed'], help='状态')
    update_parser.add_argument('--trigger-type', choices=['once', 'interval', 'cron'], help='触发方式')
    update_parser.add_argument('--interval', type=int, help='间隔秒数')
    update_parser.add_argument('--cron', help='Cron表达式')
    update_parser.add_argument('--run-at', help='执行时间 ISO格式')
    update_parser.add_argument('--training-mode', choices=['full', 'incremental'], help='训练模式')
    update_parser.add_argument('--school-id', type=int, help='学校ID (0表示全校)')
    update_parser.add_argument('--force-retrain', action='store_true', help='是否强制重新训练')

    # Delete命令
    delete_parser = subparsers.add_parser('delete', help='删除定时任务')
    delete_parser.add_argument('--id', required=True, type=int, help='任务ID')

    # Pause命令
    pause_parser = subparsers.add_parser('pause', help='暂停定时任务')
    pause_parser.add_argument('--id', required=True, type=int, help='任务ID')

    # Resume命令
    resume_parser = subparsers.add_parser('resume', help='恢复定时任务')
    resume_parser.add_argument('--id', required=True, type=int, help='任务ID')

    # Show命令
    show_parser = subparsers.add_parser('show', help='显示任务详情')
    show_parser.add_argument('--id', required=True, type=int, help='任务ID')

    # History命令
    history_parser = subparsers.add_parser('history', help='查看任务执行历史')
    history_parser.add_argument('--id', required=True, type=int, help='任务ID')
    history_parser.add_argument('--limit', type=int, default=20, help='显示记录数')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = ScheduledTasksCLI()

    try:
        if args.command == 'list':
            cli.list_tasks(status=args.status, training_mode=args.training_mode)
        elif args.command == 'create':
            cli.create_task(
                name=args.name,
                description=args.description,
                trigger_type=args.trigger_type,
                interval_seconds=args.interval,
                cron_expression=args.cron,
                run_at=args.run_at,
                training_mode=args.training_mode,
                school_id=args.school_id,
                force_retrain=args.force_retrain,
                created_by=args.created_by
            )
        elif args.command == 'update':
            cli.update_task(
                task_id=args.id,
                name=args.name,
                description=args.description,
                status=args.status,
                trigger_type=args.trigger_type,
                interval_seconds=args.interval,
                cron_expression=args.cron,
                run_at=args.run_at,
                training_mode=args.training_mode,
                school_id=args.school_id,
                force_retrain=args.force_retrain
            )
        elif args.command == 'delete':
            cli.delete_task(task_id=args.id)
        elif args.command == 'pause':
            cli.pause_task(task_id=args.id)
        elif args.command == 'resume':
            cli.resume_task(task_id=args.id)
        elif args.command == 'show':
            cli.show_task(task_id=args.id)
        elif args.command == 'history':
            cli.show_history(task_id=args.id, limit=args.limit)
    finally:
        cli.close()


if __name__ == '__main__':
    main()
