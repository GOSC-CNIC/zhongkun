from typing import Union
from datetime import timedelta, datetime, timezone
from concurrent.futures import Future

from django.utils import timezone as dj_timezone

from core.taskqueue import submit_task
from apps.app_global.task_locks import (
    screen_user_operate_log_lock, screen_service_stats_lock, screen_host_netflow_lock
)
from .workers import (
    ServiceLogSynchronizer, ServerServiceStatsWorker, ObjectServiceStatsWorker,
    HostNetflowWorker
)


def try_sync_service_log() -> Union[Future, None]:
    """
    同步服务操作日志
    """
    timed_minutes = 3
    start_time = screen_user_operate_log_lock.start_time
    nt = dj_timezone.now()
    # 上次同步时间大于指定同步周期，提交异步任务同步
    if not start_time or (nt - start_time) >= timedelta(minutes=timed_minutes):
        return submit_task(task_service_log_use_lock, kwargs={'timed_minutes': timed_minutes})

    return None


def task_service_log_use_lock(timed_minutes: int):
    """
    服务单元用户操作日志获取
    """
    nt = dj_timezone.now()
    ok, exc = screen_user_operate_log_lock.acquire(expire_time=(nt + timedelta(minutes=timed_minutes*5)))  # 先拿锁
    if not ok:  # 未拿到锁，未到过期时间返回
        if not screen_user_operate_log_lock.is_expired():
            return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not screen_user_operate_log_lock.start_time
            or (nt - screen_user_operate_log_lock.start_time) >= timedelta(minutes=timed_minutes)    # 定时周期
        ):
            screen_user_operate_log_lock.mark_start_task()  # 更新任务执行信息
            ServiceLogSynchronizer.run()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        screen_user_operate_log_lock.release(run_desc=run_desc)  # 释放锁


def try_stats_service() -> Union[Future, None]:
    timed_minutes = 3
    start_time = screen_service_stats_lock.start_time
    nt = dj_timezone.now()
    # 上次同步时间大于指定同步周期，提交异步任务同步
    if not start_time or (nt - start_time) >= timedelta(minutes=timed_minutes):
        return submit_task(task_service_stats_use_lock, kwargs={'timed_minutes': timed_minutes})

    return None


def task_service_stats_use_lock(timed_minutes: int):
    nt = dj_timezone.now()
    ok, exc = screen_service_stats_lock.acquire(expire_time=(nt + timedelta(minutes=15)))  # 先拿锁
    if not ok:  # 未拿到锁，未到过期时间返回
        if not screen_service_stats_lock.is_expired():
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
            ObjectServiceStatsWorker().run(now_timestamp=now_timestamp)
    except Exception as exc:
        run_desc = str(exc)
    finally:
        screen_service_stats_lock.release(run_desc=run_desc)  # 释放锁


def try_host_netflow() -> Union[Future, None]:
    timed_minutes = 6
    start_time = screen_host_netflow_lock.start_time
    nt = dj_timezone.now()
    # 上次同步时间大于指定同步周期，提交异步任务同步
    if not start_time or (nt - start_time) >= timedelta(minutes=timed_minutes):
        return submit_task(task_host_netflow_use_lock, kwargs={'timed_minutes': timed_minutes})

    return None


def task_host_netflow_use_lock(timed_minutes: int):
    nt = dj_timezone.now()
    ok, exc = screen_host_netflow_lock.acquire(expire_time=(nt + timedelta(minutes=15)))  # 先拿锁
    if not ok:  # 未拿到锁，未到过期时间返回
        if not screen_host_netflow_lock.is_expired():
            return

    run_desc = 'success'
    try:

        task_worker = HostNetflowWorker(minutes=timed_minutes)
        now_timestamp = task_worker.get_now_timestamp()     # 分钟对齐的时间戳
        start_time = datetime.fromtimestamp(now_timestamp, tz=timezone.utc)
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not screen_host_netflow_lock.start_time
            or (start_time - screen_host_netflow_lock.start_time) >= timedelta(minutes=timed_minutes)    # 定时周期
        ):
            screen_host_netflow_lock.mark_start_task(start_time=start_time)  # 更新任务执行信息
            task_worker.run(now_timestamp=now_timestamp)
    except Exception as exc:
        run_desc = str(exc)
    finally:
        screen_host_netflow_lock.release(run_desc=run_desc)  # 释放锁
