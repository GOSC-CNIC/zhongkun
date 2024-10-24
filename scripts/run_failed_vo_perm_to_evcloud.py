"""
遍历检查全部欠费云主机

目前只保存数据到邮件记录
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()

from django.utils import timezone as dj_timezone

from apps.servers.workers.evcloud_perms_log import EVCloudPermsWorker
from apps.app_global.task_locks import vo_server_perm_evcloud_lock


def run_task_use_lock():
    nt = dj_timezone.now()
    ok, exc = vo_server_perm_evcloud_lock.acquire(expire_time=(nt + timedelta(minutes=10)))  # 先拿锁
    if not ok:  # 未拿到锁，尝试过期释放
        vo_server_perm_evcloud_lock.release_if_expired()
        ok, exc = vo_server_perm_evcloud_lock.acquire(expire_time=(nt + timedelta(minutes=10)))  # 先拿锁
        if not ok:  # 未拿到锁退出
            print('locked and not expired')
            return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not vo_server_perm_evcloud_lock.start_time
            or (nt - vo_server_perm_evcloud_lock.start_time) >= timedelta(minutes=2)    # 定时周期
        ):
            vo_server_perm_evcloud_lock.mark_start_task()  # 更新任务执行信息
            EVCloudPermsWorker().run()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = vo_server_perm_evcloud_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            vo_server_perm_evcloud_lock.notify_unrelease()


if __name__ == "__main__":
    run_task_use_lock()
