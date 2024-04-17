import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.monitor.req_workers import ServiceReqCounter


if __name__ == "__main__":
    """
    一体云和对象存储服务总请求数统计更新, 定时执行周期可选1-24小时
    """
    ServiceReqCounter().run()
