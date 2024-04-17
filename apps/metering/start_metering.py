import os
import sys
from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()


if __name__ == "__main__":
    from apps.metering.measurers import ServerMeasurer, StorageMeasurer, DiskMeasurer
    ServerMeasurer().run()
    DiskMeasurer().run()
    StorageMeasurer().run()
