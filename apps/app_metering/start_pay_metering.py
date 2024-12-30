import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_site.settings')
setup()


if __name__ == "__main__":
    from django.conf import settings

    from core.site_configs_manager import get_pay_app_id
    from apps.app_metering.pay_metering import PayMeteringServer, PayMeteringObjectStorage

    app_id = get_pay_app_id(dj_settings=settings)
    PayMeteringServer(app_id=app_id).run()
    PayMeteringObjectStorage(app_id=app_id).run()
