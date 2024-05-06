import os
import sys
from pathlib import Path
from datetime import timedelta

from django import setup
from django.utils import timezone as dj_timezone


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.monitor.req_workers import ServiceReqCounter
from scripts.task_lock import monitor_req_count_lock


def run_task_use_lock():
    nt = dj_timezone.now()
    ok, exc = monitor_req_count_lock.acquire(expire_time=(nt + timedelta(hours=2)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not monitor_req_count_lock.start_time
            or (nt - monitor_req_count_lock.start_time) >= timedelta(hours=1)    # 定时周期
        ):
            monitor_req_count_lock.mark_start_task()  # 更新任务执行信息
            ServiceReqCounter().run()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = monitor_req_count_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            monitor_req_count_lock.notify_unrelease()


if __name__ == "__main__":
    """
    一体云和对象存储服务总请求数统计更新, 定时执行周期可选1-24小时
    """
    run_task_use_lock()
