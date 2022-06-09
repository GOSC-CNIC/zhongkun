import os
import sys
from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gosc.settings')
setup()

from django.conf import settings

payment_balance = getattr(settings, 'PAYMENT_BALANCE', {})
app_id = payment_balance.get('app_id', None)
if not app_id:
    print(f'Not set PAYMENT_BALANCE app_id')
    exit(1)


if __name__ == "__main__":
    from metering.measurers import ServerMeasurer
    from metering.pay_metering import PayMeteringServer
    ServerMeasurer().run()
    PayMeteringServer(app_id=app_id).run()
