"""
统计生成月度报表记录
"""

import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()

from apps.app_report.workers.report_generator import MonthlyReportGenerator

if __name__ == "__main__":
    MonthlyReportGenerator(log_stdout=True).run()
