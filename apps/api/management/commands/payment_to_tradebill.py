from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from bill.models import PaymentHistory, TransactionBill
from bill.managers.bill import TransactionBillManager


class Command(BaseCommand):
    help = """
        增加了交易流水表，生成历史支付记录对应的交易流水
        manage.py payment_to_tradebill
    """

    def add_arguments(self, parser):
        pass
        # parser.add_argument(
        #     '--template-id', default='', dest='template_id', type=str,
        #     help='The cash coupons of template id.',
        # )

    def handle(self, *args, **options):
        before_datetime = datetime(year=2022, month=12, day=1, tzinfo=timezone.utc)

        self.stdout.write(self.style.WARNING(f'before_datetime: {before_datetime}.'))
        self.stdout.write(self.style.WARNING(f'Update payment creation_time, and create tradebill for payment.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.create_tradebill_for_payment(before_datetime)

    def create_tradebill_for_payment(self, before_datetime: datetime):
        all_count = 0
        count = 0
        payment_time = None
        while True:
            try:
                payments = self.get_payments(payment_time=payment_time, before_datetime=before_datetime, limit=200)
                if len(payments) == 0:
                    break

                for payment in payments:
                    is_modified = self.ensure_tradebill(payment=payment)
                    payment_time = payment.payment_time
                    all_count += 1
                    if is_modified:
                        count += 1

                self.stdout.write(self.style.SUCCESS(f'Successfully: all_count={len(payments)}.'))
            except Exception as e:
                self.stdout.write(self.style.SUCCESS(f'Error, payment_time({payment_time}), {str(e)}'))
                continue

        self.stdout.write(self.style.SUCCESS(f'All Successfully: all_count={all_count}, modified: {count}.'))

    @staticmethod
    def get_payments(before_datetime: datetime, payment_time: datetime = None, limit: int = 100):
        qs = PaymentHistory.objects.filter(payment_time__lt=before_datetime).order_by('payment_time')
        if payment_time:
            qs = qs.filter(payment_time__gt=payment_time)

        return qs[0:limit]

    @staticmethod
    def ensure_tradebill(payment: PaymentHistory):
        """
        :return:
            True    # 有改变
            Fasle   # 什么都没改变
        """
        is_modified = False

        # 支付记录表后加的字段数据修正
        update_fields = []
        if payment.creation_time != payment.payment_time:
            payment.creation_time = payment.payment_time
            update_fields.append('creation_time')

        paid_amounts = -(payment.amounts + payment.coupon_amount)
        if payment.payable_amounts != paid_amounts:
            payment.payable_amounts = paid_amounts
            update_fields.append('payable_amounts')

        if update_fields:
            payment.save(update_fields=['creation_time', 'payable_amounts'])
            is_modified = True

        # 支付记录对应交易流水
        tbill = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id=payment.id
        ).first()
        if tbill is not None:
            return is_modified

        # 创建交易流水
        pay_history = payment
        TransactionBillManager.create_transaction_bill(
            subject=payment.subject, account=payment.payment_account,
            trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id=payment.id, out_trade_no=payment.order_id, trade_amounts=-payment.payable_amounts,
            amounts=pay_history.amounts, coupon_amount=pay_history.coupon_amount,
            after_balance=Decimal('0'), owner_type=pay_history.payer_type, owner_id=pay_history.payer_id,
            owner_name=pay_history.payer_name, app_service_id=pay_history.app_service_id, app_id=pay_history.app_id,
            remark=pay_history.remark, creation_time=pay_history.payment_time, operator=pay_history.executor
        )
        return True
