from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from utils.model import OwnerType
from apps.app_order.models import Order
from apps.app_wallet.managers.payment import PaymentManager


class OrderPaymentManager:
    def __init__(self):
        self.payment = PaymentManager()

    def pay_order(
            self, order,
            app_id: str,
            subject: str,
            executor: str,
            remark: str,
            coupon_ids: list = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        支付一个订单

        :param order: Order()
        :param app_id:
        :param subject: 标题
        :param executor: 支付执行人
        :param remark: 支付记录备注信息
        :param coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券，只使用余额)；
        :param only_coupon: True(只是用资源券支付)
        :param required_enough_balance: 是否要求余额必须足够支付，默认True(必须有足够的余额支付)，False(允许余额为负)
        :return: Order()
        :raises: Error, BalanceNotEnough
        """
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order.id)
                order = self._pay_order(
                    order=order, app_id=app_id, subject=subject,
                    executor=executor, remark=remark,
                    coupon_ids=coupon_ids, only_coupon=only_coupon,
                    required_enough_balance=required_enough_balance
                )
                return order
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def _pay_order(
            self, order: Order,
            app_id: str,
            subject: str,
            executor: str,
            remark: str,
            coupon_ids: list,
            only_coupon: bool,
            required_enough_balance: bool
    ):
        """
        支付一个订单

        :raises: Error
        """
        self._pre_pay_order(order=order, remark=remark)
        if order.payable_amount == Decimal(0):
            # 订单支付状态
            order.set_paid(pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'),
                           payment_history_id='')
            return order

        app_service_id = order.get_pay_app_service_id()
        if order.owner_type == OwnerType.USER.value:
            pay_history = self.payment.pay_by_user(
                user_id=order.user_id, app_id=app_id, subject=subject,
                amounts=order.payable_amount, executor=executor,
                remark=remark, order_id=order.id,
                app_service_id=app_service_id, instance_id='',
                required_enough_balance=required_enough_balance,
                coupon_ids=coupon_ids, only_coupon=only_coupon
            )
        else:
            pay_history = self.payment.pay_by_vo(
                vo_id=order.vo_id, app_id=app_id, subject=subject,
                amounts=order.payable_amount, executor=executor,
                remark=remark, order_id=order.id,
                app_service_id=app_service_id, instance_id='',
                required_enough_balance=required_enough_balance,
                coupon_ids=coupon_ids, only_coupon=only_coupon
            )

        # 订单支付状态
        balance_amount = -pay_history.amounts
        coupon_amount = -pay_history.coupon_amount
        pay_amount = balance_amount + coupon_amount
        order.set_paid(
            pay_amount=pay_amount,
            balance_amount=balance_amount,
            coupon_amount=coupon_amount,
            payment_history_id=pay_history.id
        )
        return order

    @staticmethod
    def _pre_pay_order(order: Order, remark: str):
        """
        :raises: Error
        """
        if order.status == Order.Status.PAID.value:
            raise errors.OrderPaid(_('不能支付已支付状态的订单'))
        elif order.status == Order.Status.CANCELLED.value:
            raise errors.OrderCancelled(message=_('不能支付作废状态的订单'))
        elif order.status != Order.Status.UNPAID.value:
            raise errors.OrderNotUnpaid(message=_('只允许支付待支付状态的订单'))

        if order.trading_status == order.TradingStatus.CLOSED.value:
            raise errors.OrderTradingClosed(message=_('订单交易已关闭'))
        elif order.trading_status == order.TradingStatus.COMPLETED.value:
            raise errors.OrderTradingCompleted(message=_('订单交易已完成'))
        if order.trading_status != Order.TradingStatus.OPENING.value:
            raise errors.Error(message=_('订单未处于交易中'))

        if order.owner_type not in OwnerType.values:
            raise errors.Error(message=_('订单所有者类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))
