from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from apps.metering.models import PaymentStatus, DailyStatementBase
from apps.app_wallet.managers.payment import PaymentManager


class MeteringPaymentManager:
    def __init__(self):
        self.payment = PaymentManager()

    @staticmethod
    def _pre_payment_bill_inspect(daily_statement: DailyStatementBase, remark: str):
        """
        支付bill前检查

        :raises: Error
        """
        # bill status
        if daily_statement.payment_status == PaymentStatus.PAID.value:
            raise errors.Error(message=_('不能支付已支付状态的账单'))
        elif daily_statement.payment_status == PaymentStatus.CANCELLED.value:
            raise errors.Error(message=_('不能支付作废状态的账单'))
        elif daily_statement.payment_status != PaymentStatus.UNPAID.value:
            raise errors.Error(message=_('只允许支付待支付状态的账单'))

        if daily_statement.is_owner_type_user() is None:
            raise errors.Error(message=_('支付人类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))

    def pay_daily_statement_bill(
            self, daily_statement: DailyStatementBase, app_id: str, subject: str,
            executor: str, remark: str, required_enough_balance: bool = True
    ):
        """
        支付计量计费账单

        :param daily_statement: DailyStatementBase子类对象
        :param app_id:
        :param subject: 标题
        :param executor: bill支付的执行人
        :param remark: 支付记录备注信息
        :param required_enough_balance: 是否要求余额必须足够支付，默认True(必须有足够的余额支付)，False(允许余额为负)
        :return: None
        :raises: Error
        """
        with transaction.atomic():
            bill = type(daily_statement).objects.select_for_update().get(id=daily_statement.id)
            return self._pay_daily_statement_bill(
                daily_statement=bill, app_id=app_id, subject=subject,
                executor=executor, remark=remark,
                required_enough_balance=required_enough_balance
            )

    def _pay_daily_statement_bill(
            self, daily_statement: DailyStatementBase, app_id: str, subject: str,
            executor: str, remark: str, required_enough_balance: bool
    ):
        """
        支付计量计费账单

        :param daily_statement: MeteringBase子类对象
        :param executor: bill支付的执行人
        :param remark: 备注信息
        :return: None
        :raises: Error, BalanceNotEnough
        """
        self._pre_payment_bill_inspect(daily_statement=daily_statement, remark=remark)
        if daily_statement.payable_amount == Decimal('0'):
            try:
                daily_statement.set_paid(trade_amount=Decimal('0'))
            except Exception as e:
                raise errors.Error(message=_('计量计费账单更新为已支付状态时错误.') + str(e))

            return None

        try:
            owner_id = daily_statement.get_owner_id()
            app_service_id = daily_statement.get_pay_app_service_id()
            order_id = daily_statement.id
            if daily_statement.is_owner_type_user():
                pay_history = self.payment.pay_by_user(
                    user_id=owner_id, app_id=app_id, subject=subject,
                    amounts=daily_statement.payable_amount, executor=executor,
                    remark=remark, order_id=order_id,
                    app_service_id=app_service_id, instance_id='',
                    required_enough_balance=required_enough_balance,
                    coupon_ids=None, only_coupon=False
                )
            else:
                pay_history = self.payment.pay_by_vo(
                    vo_id=owner_id, app_id=app_id, subject=subject,
                    amounts=daily_statement.payable_amount, executor=executor,
                    remark=remark, order_id=order_id,
                    app_service_id=app_service_id, instance_id='',
                    required_enough_balance=required_enough_balance,
                    coupon_ids=None, only_coupon=False
                )

            # 订单支付状态
            pay_amount = -(pay_history.amounts + pay_history.coupon_amount)
            # 账单支付状态
            daily_statement.set_paid(trade_amount=pay_amount, payment_history_id=pay_history.id)
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error.from_error(exc)
