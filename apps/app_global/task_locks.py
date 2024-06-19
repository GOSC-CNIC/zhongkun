from typing import Union, Tuple, List
import socket
import ipaddress
from datetime import datetime

from django.db import transaction
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext as _

from core import site_configs_manager
from apps.users.models import Email
from apps.users import managers as user_manager
from apps.app_global.models import TimedTaskLock


def get_local_ips() -> List[str]:
    return socket.gethostbyname_ex(socket.gethostname())[-1]
    # ipaddr = socket.gethostbyname(socket.gethostname())
    # return [ipaddr]
    # info = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET, type=socket.SOCK_DGRAM)
    # return [info[0][4][0]]


_private_networks = [
    ipaddress.IPv4Network('10.0.0.0/8'),
    ipaddress.IPv4Network('192.168.0.0/16'),
    ipaddress.IPv4Network('172.16.0.0/12'),
]


def get_local_ip_str() -> str:
    ips = get_local_ips()
    if len(ips) == 1:
        return ips[0]

    pri_addrs = []
    for addr in ips:
        try:
            ipv4_addr = ipaddress.IPv4Address(addr)
            if not ipv4_addr.is_private:    # 公网IP直接返回
                return addr

            if any(ipv4_addr in net for net in _private_networks):  # 私网
                pri_addrs.append(addr)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            pass

    if pri_addrs:
        return pri_addrs[0]

    return ''


class TaskLockManager:
    @staticmethod
    def get_task_lock_obj(task: str) -> TimedTaskLock:
        """
        获取锁对象，可查询锁状态

        """
        if task not in TimedTaskLock.Task.values:
            raise Exception(_('无效的定时任务锁标识'))

        obj, created = TimedTaskLock.objects.get_or_create(task=task)
        return obj

    @staticmethod
    def acquire_task_lock(task: str, expire_time: datetime) -> Tuple[bool, Union[None, Exception], TimedTaskLock]:
        """
        尝试获取并锁定任务锁

        :param task: 任务锁的标识
        :param expire_time: 如果获得锁，加锁锁定的过期时间，用于后面的任务执行周期拿不到锁时判断历史周期中锁是否存在未释放问题
        :return:
            False, Exception, TimedTaskLook()   # 未得到锁，互斥锁已被锁定
            True, None, TimedTaskLook()         # 拿到互斥锁
        """
        try:
            with transaction.atomic():
                task_lock = TimedTaskLock.objects.select_for_update().get(task=task)
                ok, exc, tlock = TaskLockManager._lock(task_lock=task_lock, expire_time=expire_time)
                return ok, exc, tlock
        except TimedTaskLock.DoesNotExist:
            TaskLockManager.get_task_lock_obj(task=task)
            with transaction.atomic():
                task_lock = TimedTaskLock.objects.select_for_update().get(task=task)
                ok, exc, tlock = TaskLockManager._lock(task_lock=task_lock, expire_time=expire_time)
                return ok, exc, tlock

    @staticmethod
    def _lock(task_lock: TimedTaskLock, expire_time: datetime) -> Tuple[bool, Union[None, Exception], TimedTaskLock]:
        """
        :return:
            False, Exception, TimedTaskLook()   # 未得到锁，互斥锁已被锁定
            True, None, TimedTaskLook()         # 拿到互斥锁
        """
        if task_lock.status == task_lock.Status.RUNNING.value:
            return False, Exception(f'Locking,task({task_lock.task}) is running'), task_lock

        task_lock.status = task_lock.Status.RUNNING.value
        task_lock.expire_time = expire_time
        task_lock.notify_time = None
        task_lock.save(update_fields=['status', 'expire_time', 'notify_time'])
        return True, None, task_lock

    @staticmethod
    def mark_lock_task_start(
            task_lock: TimedTaskLock, start_time: datetime = None
    ) -> Tuple[bool, Union[None, Exception], TimedTaskLock]:
        """
        更新定时任务执行信息
        """
        old_start_time = task_lock.start_time
        old_end_time = task_lock.end_time
        old_host = task_lock.host
        old_run_desc = task_lock.run_desc
        try:
            host_ipv4 = get_local_ip_str()
            task_lock.start_time = start_time if start_time else dj_timezone.now()
            task_lock.end_time = None
            task_lock.host = host_ipv4
            task_lock.run_desc = ''
            task_lock.save(update_fields=['start_time', 'end_time', 'host', 'run_desc'])
        except Exception as exc:
            task_lock.start_time = old_start_time
            task_lock.end_time = old_end_time
            task_lock.host = old_host
            task_lock.run_desc = old_run_desc
            return False, exc, task_lock

        return True, None, task_lock

    @staticmethod
    def release_task_lock(task: str, run_desc: str) -> Tuple[bool, Union[None, Exception], TimedTaskLock]:
        """
        :run_desc: 任务执行结果描述；success， 或者执行发生错误时错误信息
        :return:
            False, Exception, TimedTaskLock()   # 释放锁失败
            True, None, TimedTaskLock()         # 释放锁成功
        """
        with transaction.atomic():
            task_lock = TimedTaskLock.objects.select_for_update().get(task=task)
            ok, exc, task_lock = TaskLockManager._release(task_lock=task_lock, run_desc=run_desc)
            if not ok:
                ok, exc, task_lock = TaskLockManager._release(task_lock=task_lock, run_desc=run_desc)

            return ok, exc, task_lock

    @staticmethod
    def _release(task_lock: TimedTaskLock, run_desc: str) -> Tuple[bool, Union[None, Exception], TimedTaskLock]:
        """
        :return:
            False, Exception, TimedTaskLock()   # 释放锁失败
            True, None, TimedTaskLock()         # 释放锁成功
        """
        old_status = task_lock.status
        old_expire_time = task_lock.expire_time
        old_notify_time = task_lock.notify_time

        task_lock.status = task_lock.Status.NONE.value
        task_lock.end_time = dj_timezone.now()
        task_lock.run_desc = run_desc[0:254]
        task_lock.expire_time = None
        task_lock.notify_time = None
        try:
            task_lock.save(update_fields=['status', 'end_time', 'run_desc', 'expire_time', 'notify_time'])
        except Exception as exc:
            task_lock.status = old_status
            task_lock.expire_time = old_expire_time
            task_lock.notify_time = old_notify_time
            task_lock.end_time = None
            task_lock.run_desc = ''
            return False, exc, task_lock

        return True, None, task_lock


class TaskLock:
    """
    不要直接修改任务锁对象，通过方法操作
    """
    TaskNames = TimedTaskLock.Task

    def __init__(self, task_name: str):
        """
        各定时任务锁名定义于 TimedTaskLock.Task，各任务定义唯一对应的锁，不能混用
        """
        if task_name not in TimedTaskLock.Task.values:
            raise Exception(_('无效的定时任务锁标识'))

        self.task_name = task_name
        self._task_lock = None
        self._is_locked = False     # 锁是否已锁定

    def _ensure_lock(self):
        if not self._task_lock:
            self._task_lock = TaskLockManager.get_task_lock_obj(task=self.task_name)

    def __getattr__(self, attr):
        self._ensure_lock()
        try:
            return getattr(self._task_lock, attr)
        except AttributeError:
            return self.__getattribute__(attr)

    def save(self):
        raise Exception('TaskLock is readonly')

    def refresh(self):
        """
        从数据库重新加载锁
        """
        if self._task_lock:
            self._task_lock.refresh_from_db()
        else:
            self._ensure_lock()

    def acquire(self, expire_time: datetime):
        """
        :param expire_time: 获得锁加锁锁定时，设置锁的过期时间，用于后面的任务执行周期拿不到锁时判断历史周期中锁是否未释放
        :return:
            False, Exception   # 未得到锁，互斥锁已被锁定
            True, None         # 拿到互斥锁
        """
        if expire_time <= dj_timezone.now():
            raise Exception(_('锁过期时间必须大于当前时间'))

        ok, exc, tlock = TaskLockManager.acquire_task_lock(task=self.task_name, expire_time=expire_time)
        self._task_lock = tlock
        if ok:
            self._is_locked = True
        else:
            self._expired_unrelease_notify()

        return ok, exc

    def mark_start_task(self, start_time: datetime = None):
        """
        执行任务前，更新任务锁的任务执行信息，需要先拿到锁才能执行此函数

        如更新任务执行开始时间 “start_time”和“host”，清空“end_time”和“run_desc”

        :param start_time: 默认为当前时间；各定时器任务如果有时间对齐的需要，可以自行指定
        :return:
            False, Exception   # 失败
            True, None         # 成功
        """
        if not self._is_locked:
            raise Exception(_('需要先调用方法“acquire()”成功拿到锁后，确定执行任务前才可以调用方法"mark_start_task()"'))

        ok, exc, tlock = TaskLockManager.mark_lock_task_start(task_lock=self._task_lock, start_time=start_time)
        if not ok:
            ok, exc, tlock = TaskLockManager.mark_lock_task_start(task_lock=self._task_lock, start_time=start_time)

        self._task_lock = tlock
        return ok, exc

    def release(self, run_desc: str):
        """
        :run_desc: 任务执行结果描述；success， 或者执行发生错误时错误信息
        :return:
            False, Exception   # 释放锁失败
            True, None         # 释放锁成功
        """
        ok, exc, tlock = TaskLockManager.release_task_lock(task=self.task_name, run_desc=run_desc)
        self._task_lock = tlock
        if ok:
            self._is_locked = False

        return ok, exc

    def is_expired(self):
        """
        锁过期时间是否过期
        没有过期时间，或已过过期时间，判定过期
        """
        self._ensure_lock()
        tlock = self._task_lock
        nt = dj_timezone.now()
        if not tlock.expire_time or tlock.expire_time < nt:
            return True

        return False

    def _expired_unrelease_notify(self):
        """
        定时任务锁过期未释放发送通知
        """
        tlock: TimedTaskLock = self._task_lock
        # 锁定状态才发送通知
        if tlock.status != TimedTaskLock.Status.RUNNING.value:
            return None

        nt = dj_timezone.now()
        if not tlock.expire_time or tlock.expire_time > nt:
            return None

        # 锁过期超时
        # 已发送过通知，同一天内不再发送
        if tlock.notify_time and tlock.notify_time.date() == nt.date():
            return None

        email = self.notify_unrelease()
        return email

    def notify_unrelease(self):
        """
        锁未释放发送通知
        """
        tlock = self._task_lock
        message = f"""
您好：

{site_configs_manager.get_website_brand()} 后端服务定时任务锁（{tlock.get_task_display()}）超时未释放，请尽快手动释放锁，以防影响定时任务执行。

祝好
        """
        user_qs = user_manager.filter_user_queryset(is_federal_admin=True)
        receivers = user_qs.values_list('username', flat=True)  # [u.username for u in user_qs]
        if not receivers:
            return None

        email = Email.send_email(
            subject=_('定时任务锁过期未释放通知'),
            receivers=receivers,
            message=message,
            tag=Email.Tag.OTHER.value,
            save_db=True, is_feint=False
        )
        if email.status == Email.Status.SUCCESS.value:
            old_notify_time = tlock.notify_time
            tlock.notify_time = dj_timezone.now()
            try:
                tlock.save(update_fields=['notify_time'])
            except Exception:
                tlock.notify_time = old_notify_time

        return email


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
screen_user_operate_log_lock = TaskLock(task_name=TaskLock.TaskNames.SCREEN_USER_OPERATE_LOG.value)   # 大屏展示用户操作日志
screen_host_netflow_lock = TaskLock(task_name=TaskLock.TaskNames.SCREEN_HOST_NETFLOW.value)  # 大屏展示主机单元网络流量
netflow_update_element_lock = TaskLock(task_name=TaskLock.TaskNames.NETFLOW_UPDATE_ELEMENT.value)  # 流量图表元素更新
