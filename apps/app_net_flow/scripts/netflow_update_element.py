"""
定时更新全部的端口流量图表
"""

import os
import sys
from django import setup
from pathlib import Path

# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()

from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from scripts.task_lock import netflow_update_element_lock
from apps.app_net_flow.handlers.easyops import EasyOPS
from django.utils import timezone as dj_timezone
from datetime import timedelta
from apps.app_alert.utils.utils import DateUtils
from apps.app_alert.utils.logger import setup_logger

logger = setup_logger(__name__, __file__)


def update_elements():
    logger.info(f"当前时间：{DateUtils.now()}")
    chart_list = EasyOPS().crawler_easyops_chart_list()
    element_set = set()
    for item in chart_list:
        obj, created = ChartModel.objects.update_or_create(
            device_ip=item.get("device_ip"),
            port_name=item.get("port_name"),
            defaults=item
        )
        element_set.add(f'{item.get("device_ip")}_{item.get("port_name")}')
        logger.info(obj)
        logger.info(created)

    queryset = ChartModel.objects.all()
    for item in queryset:
        ip_port = f'{item.device_ip}_{item.port_name}'
        if ip_port not in element_set:
            menu2chart_queryset = Menu2Chart.objects.filter(chart=item)
            menu2chart_queryset.delete()
            item.delete()


def run_task_use_lock():
    nt = dj_timezone.now()
    ok, exc = netflow_update_element_lock.acquire(expire_time=(nt + timedelta(minutes=1)))  # 先拿锁
    if not ok:  # 未拿到锁退出
        return

    run_desc = 'success'
    try:
        # 成功拿到锁后，各定时任务根据锁的上周期任务执行开始时间 “lock.start_time”判断 当前任务是否需要执行（本周期其他节点可能已经执行过了）
        if (
                not netflow_update_element_lock.start_time
                or (nt - netflow_update_element_lock.start_time) >= timedelta(minutes=1)  # 定时周期
        ):
            netflow_update_element_lock.mark_start_task()  # 更新任务执行信息
            update_elements()
    except Exception as exc:
        run_desc = str(exc)
    finally:
        ok, exc = netflow_update_element_lock.release(run_desc=run_desc)  # 释放锁
        # 锁释放失败，发送通知
        if not ok:
            netflow_update_element_lock.notify_unrelease()


if __name__ == '__main__':
    run_task_use_lock()
    # update_elements()
