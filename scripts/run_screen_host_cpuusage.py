"""
大屏展示主机单元cpu使用率时许数据
"""

import os
import sys

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.app_screenvis.workers.cpu_usage import HostCpuUsageWorker


if __name__ == "__main__":
    HostCpuUsageWorker(minutes=10).run(update_before_invalid_cycles=5)
