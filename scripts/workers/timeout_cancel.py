from datetime import timedelta
import logging
import sys
from pathlib import Path

from django.utils import timezone

from order.models import Order
from order.managers import OrderManager


def config_logger(name: str = 'order-timeout-logger', level=logging.INFO, stdout: bool = False):
    log_dir = Path('/var/log/nginx')
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s ",  # 配置输出日志格式
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    if stdout:
        std_handler = logging.StreamHandler(stream=sys.stdout)
        std_handler.setFormatter(formatter)
        logger.addHandler(std_handler)

    file_handler = logging.FileHandler(filename=log_dir.joinpath("order-timeout.log"))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.WARNING)
    logger.addHandler(file_handler)
    return logger


class OrderTimeoutTask:
    TIMEOUT_MINUTE = 60

    def __init__(self, timeout_minutes: int = None, log_stdout: bool = False):
        self.logger = config_logger(stdout=log_stdout)
        if timeout_minutes:
            self.TIMEOUT_MINUTE = timeout_minutes

    def run(self):
        self.logger.warning('Start order timeout task.')
        last_creation_time = None
        while True:
            try:
                order_qs = self.get_timeout_order(self.TIMEOUT_MINUTE, limit=1, creation_time_gt=last_creation_time)
                if len(order_qs) <= 0:
                    break

                for od in order_qs:
                    try:
                        OrderManager().do_cancel_order(order_id=od.id)
                    except Exception as exc:
                        self.logger.error(f'do cancel order({od.id}) error, {str(exc)}')

                    last_creation_time = od.creation_time
            except Exception as exc:
                self.logger.error(f'error, {str(exc)}')

        self.logger.warning('End order timeout task.')

    @staticmethod
    def get_timeout_order(timeout: int, limit: int, creation_time_gt=None):
        nt = timezone.now()
        creation_time__lte = nt - timedelta(minutes=timeout)

        qs = Order.objects.filter(
            status=Order.Status.UNPAID.value, creation_time__lte=creation_time__lte).order_by('creation_time')

        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        return qs[0:limit]
