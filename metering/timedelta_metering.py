import os
import sys
from datetime import date, datetime, timedelta, timezone

from django import setup

utc = timezone.utc

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gosc.settings')
setup()

from django.conf import settings

payment_balance = getattr(settings, 'PAYMENT_BALANCE', {})
app_id = payment_balance.get('app_id', None)
if not app_id:
    print(f'Not set PAYMENT_BALANCE app_id')
    exit(1)


def server_metering_pay():
    from metering.measurers import ServerMeasurer
    from metering.pay_metering import PayMeteringServer
    from metering.statement_generators import GenerateDailyStatementServer

    now_date = datetime.utcnow().astimezone(utc).date() - timedelta(days=1)
    # start_date = date(year=2022, month=6, day=1)
    # end_date = date(year=2022, month=9, day=22)
    start_date = now_date
    end_date = now_date

    if end_date > now_date:
        end_date = now_date

    print(f'Metring Server {start_date} - {end_date}')
    metering_date = start_date
    days = 0
    while True:
        if metering_date > end_date:
            print(f'Exit Ok，metering and pay {days} days')
            break

        print(f'[{metering_date}]')
        try:
            ServerMeasurer(metering_date=metering_date).run(raise_exception=True)
            GenerateDailyStatementServer(statement_date=metering_date).run(raise_exception=True)
            PayMeteringServer(app_id=app_id, pay_date=metering_date).run()
            print(f'OK, {metering_date}')
        except Exception as e:
            print(f'FAILED, {metering_date}, {str(e)}')

        days += 1
        metering_date += timedelta(days=1)


def disk_metering_pay():
    from metering.measurers import DiskMeasurer
    from metering.pay_metering import PayMeteringDisk
    from metering.statement_generators import DiskDailyStatementGenerater

    now_date = datetime.utcnow().astimezone(utc).date() - timedelta(days=1)
    # start_date = date(year=2023, month=6, day=21)
    # end_date = date(year=2023, month=6, day=21)
    start_date = now_date
    end_date = now_date

    if end_date > now_date:
        end_date = now_date

    print(f'Metring Disk {start_date} - {end_date}')
    metering_date = start_date
    days = 0
    while True:
        if metering_date > end_date:
            print(f'Exit Ok，metering and pay {days} days')
            break

        print(f'[{metering_date}]')
        try:
            DiskMeasurer(metering_date=metering_date).run(raise_exception=True)
            DiskDailyStatementGenerater(statement_date=metering_date).run(raise_exception=True)
            PayMeteringDisk(app_id=app_id, pay_date=metering_date).run()
            print(f'OK, {metering_date}')
        except Exception as e:
            print(f'FAILED, {metering_date}, {str(e)}')

        days += 1
        metering_date += timedelta(days=1)


def storage_metering_pay():
    from metering.measurers import StorageMeasurer
    from metering.pay_metering import PayMeteringObjectStorage
    from metering.statement_generators import GenerateDailyStatementObjectStorage

    metering_date = datetime.utcnow().astimezone(utc).date() - timedelta(days=1)

    # 对象存储只计量前天的
    print(f'Metering Storage [{metering_date}]')
    try:
        StorageMeasurer(metering_date=metering_date).run()
        GenerateDailyStatementObjectStorage(statement_date=metering_date).run()
        PayMeteringObjectStorage(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


def website_monitor_metering_pay():
    from metering.measurers import MonitorWebsiteMeasurer
    from metering.statement_generators import WebsiteMonitorStatementGenerater
    from metering.pay_metering import PayMeteringWebsite

    metering_date = datetime.utcnow().astimezone(utc).date() - timedelta(days=1)

    print(f'Metering monitor website [{metering_date}]')
    try:
        MonitorWebsiteMeasurer(metering_date=metering_date).run()
        WebsiteMonitorStatementGenerater(statement_date=metering_date).run()
        PayMeteringWebsite(app_id=app_id, pay_date=metering_date).run()
        print(f'OK, {metering_date}')
    except Exception as e:
        print(f'FAILED, {metering_date}, {str(e)}')


if __name__ == "__main__":
    server_metering_pay()
    disk_metering_pay()
    website_monitor_metering_pay()
    storage_metering_pay()
