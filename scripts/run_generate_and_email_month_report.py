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

from apps.report.workers.report_generator import MonthlyReportGenerator, MonthlyReportNotifier
from scripts.task_lock import report_monthly_lock


def run_task():
    try:
        from apps.report.workers.server_notifier import ArrearServerReporter
        from apps.report.workers.storage_trend import ArrearBucketReporter
        ArrearServerReporter().run()
        ArrearBucketReporter().run()
    except Exception as exc:
        pass

    mrg = MonthlyReportGenerator(log_stdout=True)
    ok = mrg.run()
    if ok:
        MonthlyReportNotifier(report_data=mrg.report_period_date, log_stdout=True).run()


def run_task_use_lock():
    nt = dj_timezone.now()
    ok, exc = report_monthly_lock.acquire(expire_time=(nt + timedelta(hours=24)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not report_monthly_lock.start_time
            or (nt - report_monthly_lock.start_time) >= timedelta(hours=24)    # 定时周期
        ):
            report_monthly_lock.mark_start_task()  # 更新任务执行信息
            run_task()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = report_monthly_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            report_monthly_lock.notify_unrelease()


if __name__ == "__main__":
    """
    生成月度报表，并发送给用户

    遍历查询欠费的云主机和存储桶，记录到report中各资源的欠费记录表中
    """
    run_task_use_lock()
