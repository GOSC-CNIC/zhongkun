"""
大屏展示服务单元统计时序数据
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from django.utils import timezone as dj_timezone
from apps.app_screenvis.workers.service_stats import ServerServiceStatsWorker
from scripts.task_lock import screen_service_stats_lock


def main_use_lock(timed_minutes: int):
    nt = dj_timezone.now()
    ok, exc = screen_service_stats_lock.acquire(expire_time=(nt + timedelta(minutes=60)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        task_worker = ServerServiceStatsWorker(minutes=timed_minutes)
        now_timestamp = task_worker.get_now_timestamp()     # 分钟对齐的时间戳
        start_time = datetime.fromtimestamp(now_timestamp, tz=timezone.utc)
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not screen_service_stats_lock.start_time
            or (start_time - screen_service_stats_lock.start_time) >= timedelta(minutes=timed_minutes)    # 定时周期
        ):
            screen_service_stats_lock.mark_start_task(start_time=start_time)  # 更新任务执行信息
            task_worker.run(now_timestamp=now_timestamp)
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = screen_service_stats_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            screen_service_stats_lock.notify_unrelease()


if __name__ == "__main__":
    main_use_lock(timed_minutes=3)
