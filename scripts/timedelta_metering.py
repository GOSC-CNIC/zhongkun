"""
每日计量计费扣费定时任务
云主机、云硬盘、对象存储、站点监控
"""
import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

from django import setup

utc = timezone.utc

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()


from django.utils import timezone as dj_timezone

from core.site_configs_manager import get_pay_app_id
from apps.app_global.task_locks import metering_lock


def server_metering_pay(app_id: str, metering_date: date):
    from apps.app_metering.measurers import ServerMeasurer
    from apps.app_metering.pay_metering import PayMeteringServer
    from apps.app_metering.statement_generators import GenerateDailyStatementServer

    print(f'Metring Server {metering_date}')

    try:
        ServerMeasurer(metering_date=metering_date).run(raise_exception=True)
        GenerateDailyStatementServer(statement_date=metering_date).run(raise_exception=True)
        PayMeteringServer(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


def disk_metering_pay(app_id: str, metering_date: date):
    from apps.app_metering.measurers import DiskMeasurer
    from apps.app_metering.pay_metering import PayMeteringDisk
    from apps.app_metering.statement_generators import DiskDailyStatementGenerater

    print(f'Metring Disk {metering_date}')

    try:
        DiskMeasurer(metering_date=metering_date).run(raise_exception=True)
        DiskDailyStatementGenerater(statement_date=metering_date).run(raise_exception=True)
        PayMeteringDisk(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


def storage_metering_pay(app_id: str, metering_date: date):
    from apps.app_metering.measurers import StorageMeasurer
    from apps.app_metering.pay_metering import PayMeteringObjectStorage
    from apps.app_metering.statement_generators import GenerateDailyStatementObjectStorage

    # 对象存储只计量前天的
    print(f'Metering Storage [{metering_date}]')
    try:
        StorageMeasurer(metering_date=metering_date).run()
        GenerateDailyStatementObjectStorage(statement_date=metering_date).run()
        PayMeteringObjectStorage(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


def website_monitor_metering_pay(app_id: str, metering_date: date):
    from apps.app_metering.measurers import MonitorWebsiteMeasurer
    from apps.app_metering.statement_generators import WebsiteMonitorStatementGenerater
    from apps.app_metering.pay_metering import PayMeteringWebsite

    print(f'Metering monitor website [{metering_date}]')
    try:
        MonitorWebsiteMeasurer(metering_date=metering_date).run()
        WebsiteMonitorStatementGenerater(statement_date=metering_date).run()
        PayMeteringWebsite(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


def run_task(app_id: str):
    metering_date = datetime.utcnow().astimezone(utc).date() - timedelta(days=1)

    server_metering_pay(app_id=app_id, metering_date=metering_date)
    disk_metering_pay(app_id=app_id, metering_date=metering_date)
    website_monitor_metering_pay(app_id=app_id, metering_date=metering_date)
    storage_metering_pay(app_id=app_id, metering_date=metering_date)


def run_task_use_lock(app_id: str):
    nt = dj_timezone.now()
    ok, exc = metering_lock.acquire(expire_time=(nt + timedelta(hours=23)))  # 先拿锁
    if not ok:  # 未拿到锁，尝试过期释放
        metering_lock.release_if_expired()
        ok, exc = metering_lock.acquire(expire_time=(nt + timedelta(hours=23)))  # 先拿锁
        if not ok:  # 未拿到锁退出
            print('locked and not expired')
            return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
            not metering_lock.start_time
            or (nt - metering_lock.start_time) >= timedelta(hours=23)    # 定时周期
        ):
            metering_lock.mark_start_task()  # 更新任务执行信息
            run_task(app_id=app_id)
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = metering_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            metering_lock.notify_unrelease()


if __name__ == "__main__":
    try:
        pay_app_id = get_pay_app_id()
    except Exception as exc:
        print(str(exc))
        exit(1)
        raise exc

    run_task_use_lock(app_id=pay_app_id)
