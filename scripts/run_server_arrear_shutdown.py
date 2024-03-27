"""
遍历检查全部欠费云主机

目前只保存数据到邮件记录
"""

import os
import sys

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()


from scripts.workers.server_notifier import ServerArrearNotifier


if __name__ == "__main__":
    ServerArrearNotifier(log_stdout=False).run(
        only_query_to_email=True
    )
