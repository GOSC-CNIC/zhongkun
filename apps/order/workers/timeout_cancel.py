from datetime import timedelta
from django.utils import timezone

from apps.order.models import Order
from apps.order.managers import OrderManager

from core.loggers import config_script_logger


class OrderTimeoutTask:
    TIMEOUT_MINUTE = 60

    def __init__(self, timeout_minutes: int = None, log_stdout: bool = False):
        self.logger = config_script_logger(
            name='script-order-timeout-logger', filename="order-timeout.log", stdout=log_stdout)
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
