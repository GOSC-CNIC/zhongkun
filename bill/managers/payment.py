from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from utils.model import OwnerType
from bill.models import PaymentHistory, UserPointAccount, VoPointAccount
from metering.models import MeteringBase, PaymentStatus


class PaymentManager:
    @staticmethod
    def get_user_point_account(user_id: str, select_for_update: bool = False):
        if select_for_update:
            user_account = UserPointAccount.objects.select_for_update().select_related('user').filter(
                user_id=user_id).first()
        else:
            user_account = UserPointAccount.objects.select_related('user').filter(user_id=user_id).first()

        if user_account is None:
            upa = UserPointAccount(user_id=user_id, balance=Decimal(0))
            upa.save(force_insert=True)
            if select_for_update:
                user_account = UserPointAccount.objects.select_for_update().filter(user_id=user_id).first()
            else:
                user_account = upa

        return user_account

    @staticmethod
    def get_vo_point_account(vo_id: str, select_for_update: bool = False):
        if select_for_update:
            vo_account = VoPointAccount.objects.select_for_update().select_related('vo').filter(vo_id=vo_id).first()
        else:
            vo_account = VoPointAccount.objects.select_related('vo').filter(vo_id=vo_id).first()

        if vo_account is None:
            vpa = VoPointAccount(vo_id=vo_id, balance=Decimal(0))
            vpa.save(force_insert=True)
            if select_for_update:
                vo_account = VoPointAccount.objects.select_for_update().filter(vo_id=vo_id).first()
            else:
                vo_account = vpa

        return vo_account

    def has_enough_balance_user(self, user_id: str, money_amount: Decimal):
        """
        用户是否有足够的余额
        :return:
            True        # 满足
            False
        """
        user_account = self.get_user_point_account(user_id=user_id)
        return user_account.balance >= money_amount

    def has_enough_balance_vo(self, vo_id: str, money_amount: Decimal):
        """
        vo组是否有足够的余额
        :return:
            True        # 满足
            False
        """
        vo_account = self.get_vo_point_account(vo_id=vo_id)
        return vo_account.balance >= money_amount

    @staticmethod
    def _pre_payment_inspect(metering_bill: MeteringBase, remark: str):
        """
        支付bill前检查

        :raises: Error
        """
        # bill status
        if metering_bill.payment_status == PaymentStatus.PAID.value:
            raise errors.Error(message=_('不能支付已支付状态的账单'))
        elif metering_bill.payment_status == PaymentStatus.CANCELLED.value:
            raise errors.Error(message=_('不能支付作废状态的账单'))
        elif metering_bill.payment_status != PaymentStatus.UNPAID.value:
            raise errors.Error(message=_('只允许支付待支付状态的账单'))

        if metering_bill.is_owner_type_user() is None:
            raise errors.Error(message=_('支付人类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))

    def pay_metering_bill(self, metering_bill: MeteringBase, executor: str, remark: str):
        """
        支付计量计费账单

        :param metering_bill: MeteringBase子类对象
        :param executor: bill支付的执行人
        :param remark: 备注信息

        :raises: Error
        """
        self._pre_payment_inspect(metering_bill=metering_bill, remark=remark)
        if not metering_bill.is_postpaid():
            try:
                metering_bill.set_paid(trade_amount=Decimal(0))
            except Exception as e:
                raise errors.Error(message=_('计量计费账单更新为已支付状态时错误.') + str(e))

            return None

        try:
            owner_id = metering_bill.get_owner_id()
            if metering_bill.is_owner_type_user():
                return self._pay_user_bill(bill=metering_bill, payer_id=owner_id, executor=executor, remark=remark)
            else:
                return self._pay_vo_bill(bill=metering_bill, payer_id=owner_id, executor=executor, remark=remark)
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def _pay_user_bill(self, bill: MeteringBase, payer_id: str, executor: str, remark: str) -> Decimal:
        with transaction.atomic():
            user_account = self.get_user_point_account(user_id=payer_id, select_for_update=True)
            self.__do_pay_bill(
                account=user_account, bill=bill, payer_id=payer_id, payer_name=user_account.user.username,
                payer_type=OwnerType.USER.value, executor=executor, remark=remark
            )

        return user_account.balance

    def _pay_vo_bill(self, bill: MeteringBase, payer_id: str, executor: str, remark: str) -> Decimal:
        with transaction.atomic():
            vo_account = self.get_vo_point_account(vo_id=payer_id, select_for_update=True)
            self.__do_pay_bill(
                account=vo_account, bill=bill, payer_id=payer_id, payer_name=vo_account.vo.name,
                payer_type=OwnerType.VO.value, executor=executor, remark=remark
            )

        return vo_account.balance

    @staticmethod
    def __do_pay_bill(
            account, bill: MeteringBase, payer_id: str, payer_name: str, payer_type: str, executor: str, remark: str
    ):
        before_payment = account.balance
        trade_amount = bill.original_amount
        after_payment = before_payment - trade_amount
        history_amounts = - trade_amount
        history_type = PaymentHistory.Type.PAYMENT.value

        # 账户扣款
        account.balance = after_payment
        account.save(update_fields=['balance'])

        # 支付记录
        pay_history = PaymentHistory(
            payment_account=account.id,
            payment_method=PaymentHistory.PaymentMethod.BALANCE.value,
            executor=executor,
            payer_id=payer_id,
            payer_name=payer_name,
            payer_type=payer_type,
            amounts=history_amounts,
            before_payment=before_payment,
            after_payment=after_payment,
            type=history_type,
            remark=remark,
            order_id='',
            resource_type=bill.get_resource_type(),
            service_id=bill.get_service_id(),
            instance_id=bill.get_instance_id()
        )
        pay_history.save(force_insert=True)

        # 账单支付状态
        bill.set_paid(trade_amount=trade_amount, payment_history_id=pay_history.id)
        return True
