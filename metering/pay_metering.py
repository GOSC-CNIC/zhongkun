from datetime import date

from metering.models import PaymentStatus, DailyStatementServer
from metering.payment import MeteringPaymentManager


class PayMeteringServer:
    def __init__(self, app_id: str, pay_date: date = None):
        """
        :param pay_date: 指定只扣费那个计费日的云主机日结算单
        """
        self.app_id = app_id
        self.pay_date = pay_date
        self.count = 0
        self.success_count = 0
        self.failed_count = 0

    def start_print(self):
        print('开始扣费云主机日结算单')
        if self.pay_date:
            print(f'指定只扣费{self.pay_date}日期的云主机日结算单')

        print(f'本次要扣费的云主机日结算单总数：{self.count}')

    def run(self):
        queryset = self.get_metering_queryset()
        self.count = queryset.count()
        self.start_print()

        last_creation_time = None
        while True:
            meterings = self.get_metering(creation_time_gt=last_creation_time)
            m_length = len(meterings)
            if m_length == 0:
                break

            for m in meterings:
                ok = self.do_pay_one_bill(bill=m)
                if ok:
                    self.success_count += 1
                else:
                    self.failed_count += 1

                last_creation_time = m.creation_time

            print(f'Pay {m_length} meterings.')

        print(f'总数：{self.count}, 扣费成功：{self.success_count}, 扣费失败：{self.failed_count}.')

    def get_metering(self, creation_time_gt=None, limit: int = 100):
        queryset = self.get_metering_queryset()

        if creation_time_gt:
            queryset = queryset.filter(creation_time__gt=creation_time_gt)

        queryset = queryset.order_by('creation_time')
        return queryset[0:limit]

    def get_metering_queryset(self):
        queryset = DailyStatementServer.objects.filter(payment_status=PaymentStatus.UNPAID.value)
        if self.pay_date:
            queryset = queryset.filter(date=self.pay_date)

        return queryset

    def do_pay_one_bill(self, bill: DailyStatementServer):
        pay_mgr = MeteringPaymentManager()
        remark = f'server, {bill.date}'
        try:
            pay_mgr.pay_daily_statement_bill(
                daily_statement=bill, app_id=self.app_id, subject='云服务器按量计费',
                executor='metering', remark=remark, required_enough_balance=False
            )
        except Exception as exc:
            try:
                pay_mgr.pay_daily_statement_bill(
                    daily_statement=bill, app_id=self.app_id, subject='云服务器按量计费',
                    executor='metering', remark=remark, required_enough_balance=False
                )
            except Exception as exc:
                print(f'[Failed] 云主机日结算单（id={bill.id}）扣费失败，{exc}')
                return False

        return True
