import os
import sys

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from scripts.workers.req_logs import LogSiteReqCounter


if __name__ == "__main__":
    """
    更新无效的站点日志请求数统计时序数据占位记录
    """
    LogSiteReqCounter(minutes=1).run_update_invalid(before_minutes=60)
