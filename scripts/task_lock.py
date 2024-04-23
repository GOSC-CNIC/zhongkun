from apps.app_global.task_locks import TaskLock


"""
各定时任务使用各自的锁

锁的使用步骤：
ok, exc = lock.acquire(expire_time)    # 先拿锁
if not ok:  未拿到锁退出
    return

run_desc='success'
try:
    # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
    if 满足执行条件:
        lock.mark_start_task()  # 更新任务执行信息
        do_task()
except Exception as exc:
    处理错误
    run_desc = str(exc)
finally:
    ok, exc = lock.release(run_desc=run_desc)  # 释放锁
    # 锁释放失败，发送通知
    if not ok:
        lock.notify_unrelease()
"""

metering_lock = TaskLock(task_name=TaskLock.TaskNames.METERING.value)   # 计量计费
bucket_monthly_lock = TaskLock(task_name=TaskLock.TaskNames.BKT_MONTHLY.value)   # 存储桶月度统计
report_monthly_lock = TaskLock(task_name=TaskLock.TaskNames.REPORT_MONTHLY.value)   # 月度报表
monitor_log_time_count_lock = TaskLock(task_name=TaskLock.TaskNames.LOG_TIME_COUNT.value)   # 日志时序统计
monitor_req_count_lock = TaskLock(task_name=TaskLock.TaskNames.REQ_COUNT.value)   # 服务请求量统计
scan_lock = TaskLock(task_name=TaskLock.TaskNames.SCAN.value)   # 安全扫描
screen_host_cpuusage_lock = TaskLock(task_name=TaskLock.TaskNames.SCREEN_HOST_CPUUSAGE.value)   # 大屏展示主机CPU使用率
screen_service_stats_lock = TaskLock(task_name=TaskLock.TaskNames.SCREEN_SERVICE_STATS.value)   # 大屏展示服务单元统计数据
alert_email_notify_lock = TaskLock(task_name=TaskLock.TaskNames.ALERT_EMAIL.value)   # 告警邮件通知
alert_dingtalk_notify_lock = TaskLock(task_name=TaskLock.TaskNames.ALERT_DINGTALK.value)   # 告警钉钉通知
