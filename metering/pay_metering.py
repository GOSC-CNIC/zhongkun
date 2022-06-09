from bill.managers import PaymentManager
from metering.models import MeteringServer, PaymentStatus


class PayMeteringServer:
    def __init__(self, app_id: str):
        self.app_id = app_id

    def run(self):
        last_creation_time = None
        pay_mgr = PaymentManager()
        while True:
            meterings  = self.get_metering(creation_time_gt=last_creation_time)
            if len(meterings) == 0:
                break

            for m in meterings:
                pay_mgr.pay_metering_bill(
                    metering_bill=m, app_id=self.app_id, subject='云服务器计费',
                    executor='metering', remark='按量计费', required_enough_balance=False
                )
                last_creation_time = m.creation_time

    def get_metering(self, creation_time_gt=None, limit: int = 100):
        queryset = MeteringServer.objects.filter(payment_status=PaymentStatus.UNPAID.value)
        if creation_time_gt:
            queryset = queryset.filter(creation_time__gt=creation_time_gt)

        queryset = queryset.order_by('creation_time')
        return queryset[0:limit]

