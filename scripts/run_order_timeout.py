"""
未支付订单超时取消
"""

import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()


from apps.order.workers.timeout_cancel import OrderTimeoutTask


if __name__ == "__main__":
    OrderTimeoutTask(timeout_minutes=60*24*7, log_stdout=False).run()
