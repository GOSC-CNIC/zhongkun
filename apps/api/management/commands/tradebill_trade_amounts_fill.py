from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from bill.models import PaymentHistory, TransactionBill, RefundRecord


class Command(BaseCommand):
    help = """
        交易流水表后添加的字段（交易金额，外部交易编号）填充
        manage.py tradebill_trade_amounts_fill --before-time="2022-12-26T00:00:00+08:00"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--before-time', default=None, dest='before-time', type=str,
            help='The trade bill before the time.',
        )

    def handle(self, *args, **options):
        before_time_str = options.get('before-time')
        if before_time_str:
            try:
                before_datetime = datetime.fromisoformat(before_time_str)
            except ValueError as e:
                raise CommandError(str(e))
        else:
            before_datetime = timezone.now()

        self.stdout.write(self.style.WARNING(f'before_datetime: {before_datetime}.'))
        self.stdout.write(self.style.WARNING(f'Fill tradebill trade_amounts、out_trade_no.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.tradebill_trade_amount_fill(before_datetime)

    def tradebill_trade_amount_fill(self, before_datetime: datetime):
        all_count = 0
        count = 0
        creation_time = None
        while True:
            try:
                tradebills = self.get_trade_bills(
                    creation_time=creation_time, before_datetime=before_datetime, limit=200)
                if len(tradebills) == 0:
                    break

                for tbill in tradebills:
                    is_modified = self.ensure_tradebill(tbill=tbill)
                    creation_time = tbill.creation_time
                    all_count += 1
                    if is_modified:
                        count += 1

                self.stdout.write(self.style.SUCCESS(f'Successfully: all_count={len(tradebills)}.'))
            except Exception as e:
                self.stdout.write(self.style.SUCCESS(f'Error, creation_time({creation_time}), {str(e)}'))
                continue

        self.stdout.write(self.style.SUCCESS(f'All Successfully: all_count={all_count}, modified: {count}.'))

    @staticmethod
    def get_trade_bills(before_datetime: datetime, creation_time: datetime = None, limit: int = 100):
        qs = TransactionBill.objects.filter(creation_time__lt=before_datetime).order_by('creation_time')
        if creation_time:
            qs = qs.filter(creation_time__gt=creation_time)

        return qs[0:limit]

    def ensure_tradebill(self, tbill: TransactionBill):
        """
        :return:
            True    # 有改变
            Fasle   # 什么都没改变
        """
        # 交易流水记录表后加的字段数据修正
        update_fields = []
        trade_amounts = tbill.amounts + tbill.coupon_amount
        if tbill.trade_amounts != trade_amounts:
            tbill.trade_amounts = trade_amounts
            update_fields.append('trade_amounts')

        if not tbill.out_trade_no:
            out_trade_no = self.get_trade_bill_out_trade_no(tbill=tbill)
            if out_trade_no:
                tbill.out_trade_no = out_trade_no
                update_fields.append('out_trade_no')

        if update_fields:
            tbill.save(update_fields=update_fields)
            return True

        return False

    def get_trade_bill_out_trade_no(self, tbill: TransactionBill):
        # 支付
        if tbill.trade_type == tbill.TradeType.PAYMENT.value:
            pay: PaymentHistory = PaymentHistory.objects.filter(id=tbill.trade_id).first()
            if pay is None:
                out_trade_no = ''
                self.stdout.write(self.style.WARNING(
                    f'Tradebill({tbill.id})，Payment trade_id({tbill.trade_id}) is not exists.'))
            else:
                out_trade_no = pay.order_id
        # 退款
        elif tbill.trade_type == tbill.TradeType.REFUND.value:
            refund: RefundRecord = RefundRecord.objects.filter(id=tbill.trade_id).first()
            if refund is None:
                out_trade_no = ''
                self.stdout.write(self.style.WARNING(
                    f'Tradebill({tbill.id})，Refund trade_id({tbill.trade_id}) is not exists.'))
            else:
                out_trade_no = refund.out_refund_id
        else:
            out_trade_no = ''

        return out_trade_no
