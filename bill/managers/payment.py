from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from utils.model import OwnerType
from bill.models import Bill, PaymentHistory, UserPointAccount, VoPointAccount


class PaymentManager:
    def get_user_point_account(self, user_id: str, select_for_update: bool = False):
        if select_for_update:
            user_account = UserPointAccount.objects.select_for_update().filter(user_id=user_id).first()
        else:
            user_account = UserPointAccount.objects.filter(user_id=user_id).first()

        if user_account is None:
            upa = UserPointAccount(user_id=user_id, balance=Decimal(0))
            upa.save(force_insert=True)
            if select_for_update:
                user_account = UserPointAccount.objects.select_for_update().filter(user_id=user_id).first()
            else:
                user_account = upa

        return user_account

    def get_vo_point_account(self, vo_id: str, select_for_update: bool = False):
        if select_for_update:
            vo_account = VoPointAccount.objects.select_for_update().filter(vo_id=vo_id).first()
        else:
            vo_account = VoPointAccount.objects.filter(vo_id=vo_id).first()

        if vo_account is None:
            vpa = VoPointAccount(vo_id=vo_id, balance=Decimal(0))
            vpa.save(force_insert=True)
            if select_for_update:
                vo_account = VoPointAccount.objects.select_for_update().filter(vo_id=vo_id).first()
            else:
                vo_account = vpa

        return vo_account

    @staticmethod
    def pre_payment_inspect(bill: Bill, remark: str):
        """
        支付bill前检查

        :raises: Error
        """
        # bill status
        if bill.status == Bill.Status.PREPAID.value:
            raise errors.Error(message=_('不能支付已支付状态的账单'))
        elif bill.status == Bill.Status.CANCELLED.value:
            raise errors.Error(message=_('不能支付作废状态的账单'))
        elif bill.status != Bill.Status.UNPAID.value:
            raise errors.Error(message=_('只允许支付待支付状态的账单'))

        # bill type
        if bill.type not in Bill.Type.values:
            raise errors.Error(message=_('账单的类型无效'))

        if bill.owner_type not in OwnerType.values:
            raise errors.Error(message=_('支付人类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))

    def pay_bill(self, bill: Bill, payer_name: str, remark: str):
        """
        支付账单

        :raises: Error
        """
        self.pre_payment_inspect(bill=bill, remark=remark)

        try:
            if bill.owner_type == OwnerType.USER.value:
                return self._pay_user_bill(bill=bill, payer_id=bill.user_id, payer_name=payer_name, remark=remark)
            else:
                return self._pay_vo_bill(bill=bill, payer_id=bill.vo_id, payer_name=payer_name, remark=remark)
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def _pay_user_bill(self, bill: Bill, payer_id: str, payer_name: str, remark: str) -> Decimal:
        with transaction.atomic():
            user_account = self.get_user_point_account(user_id=payer_id, select_for_update=True)
            self.__do_pay_bill(
                account=user_account, bill=bill, payer_id=payer_id, payer_name=payer_name,
                payer_type=OwnerType.USER.value, remark=remark
            )

        return user_account.balance

    def _pay_vo_bill(self, bill: Bill, payer_id: str, payer_name: str, remark: str) -> Decimal:
        with transaction.atomic():
            vo_account = self.get_vo_point_account(vo_id=payer_id, select_for_update=True)
            self.__do_pay_bill(
                account=vo_account, bill=bill, payer_id=payer_id, payer_name=payer_name,
                payer_type=OwnerType.VO.value, remark=remark
            )

        return vo_account.balance

    def __do_pay_bill(
            self, account, bill: Bill, payer_id: str, payer_name: str, payer_type: str, remark: str
    ):
        before_payment = account.balance
        if bill.type == Bill.Type.REFUND.value:
            history_amounts = bill.amounts
            history_type = PaymentHistory.Type.REFUND.value
        else:
            history_amounts = - bill.amounts
            history_type = PaymentHistory.Type.PAYMENT.value

        after_payment = before_payment + history_amounts

        # 账户扣款
        account.balance = after_payment
        account.save(update_fields=['balance'])

        # 支付记录
        pay_history = PaymentHistory(
            payer_id=payer_id,
            payer_name=payer_name,
            payer_type=payer_type,
            amounts=history_amounts,
            before_payment=before_payment,
            after_payment=after_payment,
            type=history_type,
            bill=bill,
            remark=remark
        )
        pay_history.save(force_insert=True)

        # 账单支付状态
        bill.status = Bill.Status.PREPAID
        bill.save(update_fields=['status'])
        return True
