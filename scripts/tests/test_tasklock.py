import ipaddress
from datetime import datetime, timedelta

from django.utils import timezone as dj_timezone
from django.test import TestCase
from django.core import mail as dj_mail

from utils.test import get_or_create_user
from scripts.models import TimedTaskLook
from scripts.task_lock import TaskLock


class TaskLockTests(TestCase):
    def setUp(self):
        pass

    def test_lock(self):
        user1 = get_or_create_user(username='lisi@cnic.cn')
        user2 = get_or_create_user(username='zhangsan@qq.com')
        user2.set_federal_admin()

        # 不存在自动创建锁
        meter_lock = TaskLock(task_name=TimedTaskLook.Task.METERING.value)
        self.assertEqual(TimedTaskLook.objects.filter(task=TimedTaskLook.Task.METERING.value).count(), 0)
        self.assertIsNone(meter_lock._task_lock)
        self.assertEqual(meter_lock.status, TimedTaskLook.Status.NONE.value)
        self.assertEqual(TimedTaskLook.objects.filter(task=TimedTaskLook.Task.METERING.value).count(), 1)
        self.assertIsNone(meter_lock.start_time)
        self.assertIsNone(meter_lock.end_time)
        self.assertIsNone(meter_lock.expire_time)
        self.assertIsNone(meter_lock.notify_time)
        self.assertEqual(meter_lock.host, '')
        self.assertEqual(meter_lock.run_desc, '')

        # 锁过期时间无效
        with self.assertRaises(Exception):
            meter_lock.acquire(expire_time=dj_timezone.now())

        # 正常锁流程测试
        expire_time = dj_timezone.now() + timedelta(minutes=5)
        ok, exc = meter_lock.acquire(expire_time=expire_time)
        self.assertTrue(ok)
        self.assertEqual(meter_lock.status, TimedTaskLook.Status.RUNNING.value)
        self.assertEqual(meter_lock.expire_time, expire_time)
        self.assertIsNone(meter_lock.start_time)
        self.assertIsNone(meter_lock.notify_time)

        start_time = dj_timezone.now()
        ok, exc = meter_lock.mark_start_task(start_time=start_time)
        self.assertTrue(ok)
        self.assertEqual(meter_lock.status, TimedTaskLook.Status.RUNNING.value)
        self.assertEqual(meter_lock.expire_time, expire_time)
        self.assertEqual(meter_lock.start_time, start_time)
        self.assertIsNone(meter_lock.end_time)
        self.assertIsNone(meter_lock.notify_time)
        ipaddress.ip_address(meter_lock.host)
        self.assertEqual(meter_lock.run_desc, '')

        ok, exc = meter_lock.release(run_desc='success')
        self.assertTrue(ok)
        self.assertEqual(meter_lock.status, TimedTaskLook.Status.NONE.value)
        self.assertIsNone(meter_lock.expire_time)
        self.assertEqual(meter_lock.start_time, start_time)
        self.assertIsInstance(meter_lock.end_time, datetime)
        self.assertIsNone(meter_lock.notify_time)
        ipaddress.ip_address(meter_lock.host)
        self.assertEqual(meter_lock.run_desc, 'success')

        #
        self.assertEqual(len(dj_mail.outbox), 0)
        meter_lock.refresh()
        self.assertEqual(meter_lock.status, TimedTaskLook.Status.NONE.value)
        self.assertIsNone(meter_lock.expire_time)
        expire_time = dj_timezone.now() + timedelta(minutes=5)
        ok, exc = meter_lock.acquire(expire_time=expire_time)
        self.assertTrue(ok)

        # 未过期，不发邮件
        ok, exc = meter_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 0)

        # 过期，发邮件
        lock_obj = TimedTaskLook.objects.get(task=TimedTaskLook.Task.METERING.value)
        lock_obj.expire_time = dj_timezone.now()
        lock_obj.save(update_fields=['expire_time'])
        ok, exc = meter_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 1)

        # 过期，不重复发邮件
        lock_obj = TimedTaskLook.objects.get(task=TimedTaskLook.Task.METERING.value)
        lock_obj.expire_time = dj_timezone.now()
        lock_obj.save(update_fields=['expire_time'])
        ok, exc = meter_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 1)

        # 不存在自动创建锁
        alert_lock = TaskLock(task_name=TimedTaskLook.Task.ALERT_EMAIL.value)
        self.assertEqual(TimedTaskLook.objects.filter(task=TimedTaskLook.Task.ALERT_EMAIL.value).count(), 0)
        self.assertIsNone(alert_lock._task_lock)
        self.assertEqual(alert_lock.status, TimedTaskLook.Status.NONE.value)
        self.assertEqual(TimedTaskLook.objects.filter(task=TimedTaskLook.Task.METERING.value).count(), 1)
        self.assertEqual(TimedTaskLook.objects.count(), 2)
        self.assertIsNone(alert_lock.start_time)
        self.assertIsNone(alert_lock.end_time)
        self.assertIsNone(alert_lock.expire_time)
        self.assertIsNone(alert_lock.notify_time)
        self.assertEqual(alert_lock.host, '')
        self.assertEqual(alert_lock.run_desc, '')

        # 锁过期时间无效
        with self.assertRaises(Exception):
            alert_lock.acquire(expire_time=dj_timezone.now())

        # 正常锁流程未释放锁测试
        expire_time = dj_timezone.now() + timedelta(minutes=1)
        ok, exc = alert_lock.acquire(expire_time=expire_time)
        self.assertTrue(ok)
        self.assertEqual(alert_lock.status, TimedTaskLook.Status.RUNNING.value)
        self.assertEqual(alert_lock.expire_time, expire_time)
        self.assertIsNone(alert_lock.start_time)
        self.assertIsNone(alert_lock.notify_time)

        ok, exc = alert_lock.mark_start_task()
        self.assertTrue(ok)
        self.assertEqual(alert_lock.status, TimedTaskLook.Status.RUNNING.value)
        self.assertEqual(alert_lock.expire_time, expire_time)
        self.assertIsInstance(alert_lock.start_time, datetime)
        self.assertIsNone(alert_lock.end_time)
        self.assertIsNone(alert_lock.notify_time)
        ipaddress.ip_address(alert_lock.host)
        self.assertEqual(alert_lock.run_desc, '')

        # 未过期，不发邮件
        ok, exc = alert_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 1)

        # 过期，发邮件
        lock_obj = TimedTaskLook.objects.get(task=TimedTaskLook.Task.ALERT_EMAIL.value)
        lock_obj.expire_time = dj_timezone.now()
        lock_obj.save(update_fields=['expire_time'])
        ok, exc = alert_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 2)

        # 过期，不重复发邮件
        lock_obj = TimedTaskLook.objects.get(task=TimedTaskLook.Task.ALERT_EMAIL.value)
        lock_obj.expire_time = dj_timezone.now()
        lock_obj.save(update_fields=['expire_time'])
        ok, exc = alert_lock.acquire(expire_time=expire_time)
        self.assertFalse(ok)
        self.assertEqual(len(dj_mail.outbox), 2)
