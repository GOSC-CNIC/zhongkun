import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.monitor.req_workers import LogSiteReqCounter


if __name__ == "__main__":
    """
    更新无效的站点日志请求数统计时序数据占位记录
    """
    LogSiteReqCounter(minutes=1).run_update_invalid(before_minutes=60)
