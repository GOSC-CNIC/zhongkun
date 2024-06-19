import os
import sys
from pathlib import Path
from datetime import timedelta, datetime, timezone

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()

from django.utils import timezone as dj_timezone
from apps.monitor.req_workers import LogSiteReqCounter
from apps.app_global.task_locks import monitor_log_time_count_lock


def main_use_lock(timed_minutes: int):
    nt = dj_timezone.now()
    ok, exc = monitor_log_time_count_lock.acquire(expire_time=(nt + timedelta(minutes=5)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:

        task_worker = LogSiteReqCounter(minutes=timed_minutes)
        now_timestamp = task_worker.get_now_timestamp()     # 分钟对齐的时间戳
        start_time = datetime.fromtimestamp(now_timestamp, tz=timezone.utc)
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not monitor_log_time_count_lock.start_time
            or (start_time - monitor_log_time_count_lock.start_time) >= timedelta(minutes=timed_minutes)    # 定时周期
        ):
            monitor_log_time_count_lock.mark_start_task(start_time=start_time)  # 更新任务执行信息
            task_worker.run(update_before_invalid_cycles=5, now_timestamp=now_timestamp)
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = monitor_log_time_count_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            monitor_log_time_count_lock.notify_unrelease()


if __name__ == "__main__":
    """
    站点日志请求数统计时序数据
    """
    main_use_lock(timed_minutes=1)
    # LogSiteReqCounter(minutes=1).run(update_before_invalid_cycles=5)
