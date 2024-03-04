from typing import List
from decimal import Decimal

from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.db import transaction

from core import errors
from bill.managers.payment import PaymentManager
from order.models import Order, OrderRefund, Resource
from order.managers.order import OrderManager


class OrderRefundManager:

    @staticmethod
    def get_order_refund(refund_id: str, select_for_update: bool = False) -> OrderRefund:
        if select_for_update:
            refund = OrderRefund.objects.select_related('order').select_for_update().filter(id=refund_id).first()
        else:
            refund = OrderRefund.objects.select_related('order').filter(id=refund_id).first()

        return refund

    @staticmethod
    def filter_refund_qs(order_id: str, status_in: List[str], is_delete: bool = None):
        lookups = {}
        if order_id:
            lookups['order_id'] = order_id

        if status_in:
            if len(status_in) == 1:
                lookups['status'] = status_in[0]
            else:
                lookups['status__in'] = status_in

        if is_delete is not None:
            lookups['deleted'] = is_delete

        return OrderRefund.objects.filter(**lookups).order_by('-creation_time')

    @staticmethod
    def check_order_pre_refund(order: Order) -> List[Resource]:
        """
        在订单退订前，检查订单的交易状态

        * 此方法需要在事务中调用
        """
        order_id = order.id
        OrderManager.can_deliver_or_refund_for_order(order)

        resources = OrderManager.get_order_resources(order_id=order_id, select_for_update=True)
        res_len = len(resources)
        if order.number != res_len:
            raise errors.ConflictError(message=_('订单资源记录数量和订单订购数量不一致'))

        undeliver_resources = []
        for res in resources:
            if res.order_id != order_id:
                raise errors.OrderStatusUnknown(message=_('订单和订单资源不匹配'))

            if res.instance_status == res.InstanceStatus.SUCCESS.value:
                continue

            undeliver_resources.append(res)

        if not undeliver_resources:
            raise errors.OrderTradingCompleted(message=_('订单没有可退订的未交付资源'))

        return undeliver_resources

    def create_order_refund(self, order: Order, reason: str) -> OrderRefund:
        """
        为订单创建一个退订退款单

        :raises: Error
        """
        with transaction.atomic(durable=True):
            return self._create_order_refund(order=order, reason=reason)

    def _create_order_refund(self, order: Order, reason: str) -> OrderRefund:
        """
        为订单创建一个退订退款单

        * 此函数需在事务中执行
        :raises: Error
        """
        order = OrderManager.get_order(order_id=order.id, select_for_update=True)
        undeliver_resources = self.check_order_pre_refund(order=order)
        refund_res_num = len(undeliver_resources)
        order_number = order.number
        if order_number <= 0:
            raise errors.ConflictError(message=_('订单订购资源数量无效'))

        order_amount = order.pay_amount
        if refund_res_num >= order_number:     # 全额退款
            refund_amount = order_amount
        else:
            refund_amount = order_amount * Decimal.from_float(refund_res_num / order_number)

        if refund_amount > Decimal('0.00') and not order.payment_history_id:
            raise errors.ConflictError(message=_('订单没有支付记录信息'))

        nt = dj_timezone.now()
        refund = OrderRefund(
            order=order,
            order_amount=order_amount,
            payment_history_id=order.payment_history_id,
            status=OrderRefund.Status.WAIT.value,
            status_desc='',
            creation_time=nt,
            update_time=nt,
            resource_type=order.resource_type,
            number=refund_res_num,
            reason=reason,
            refund_amount=refund_amount,
            balance_amount=Decimal('0'),
            coupon_amount=Decimal('0'),
            refund_history_id='',
            refunded_time=None,
            user_id=order.user_id,
            username=order.username,
            vo_id=order.vo_id,
            vo_name=order.vo_name,
            owner_type=order.owner_type,
            deleted=False
        )
        refund.save(force_insert=True)
        order.status = Order.Status.REFUNDING.value
        order.save(update_fields=['status'])
        return refund

    @staticmethod
    def check_pre_do_refund(order_refund: OrderRefund):
        if order_refund.deleted:
            raise errors.TargetNotExist(message=_('退订退款单已删除'))

        if order_refund.status == OrderRefund.Status.REFUNDED.value:
            raise errors.ConflictError(message=_('退订退款单已完成退款'), code='StatusRefunded')
        elif order_refund.status == OrderRefund.Status.CANCELLED.value:
            raise errors.ConflictError(message=_('退订退款单已取消作废'), code='StatusCancelled')
        elif order_refund.status not in [OrderRefund.Status.WAIT.value, OrderRefund.Status.FAILED.value]:
            raise errors.ConflictError(message=_('退订退款单状态未知，无法完成退款'), code='StatusUnknown')

        if order_refund.refund_history_id != '' or order_refund.refunded_time:
            raise errors.ConflictError(message=_('退订退款单已更新了退款编号和退款时间，无法完成退款，请联系服务人员处理。'))

    def do_refund(self, order_refund: OrderRefund, app_id: str, is_refund_coupon: bool = True) -> OrderRefund:
        refund = None
        try:
            with transaction.atomic(durable=True):
                refund = self.get_order_refund(refund_id=order_refund.id, select_for_update=True)
                if refund is None:
                    raise errors.TargetNotExist(message=_('退订退款单不存在'))
                # 退款前检查
                self.check_pre_do_refund(order_refund=order_refund)
                # 退款为0
                if order_refund.refund_amount <= Decimal('0.00'):
                    # 更新退订单状态
                    refund = self.set_refund_success(
                        refund=refund, refund_history_id='',
                        balance_amount=Decimal('0.00'), coupon_amount=Decimal('0.00'))

                    return refund

                # 钱包退款
                pay_refund = PaymentManager().refund_for_payment_id(
                    app_id=app_id, payment_id=order_refund.payment_history_id,
                    out_refund_id=order_refund.id, refund_amounts=order_refund.refund_amount,
                    refund_reason=refund.reason, remark='', is_refund_coupon=is_refund_coupon
                )
                # 退款失败，抛出错误回滚事务
                if pay_refund.status != pay_refund.Status.SUCCESS.value:
                    raise errors.Error(message=_('钱包退款失败') + pay_refund.status_desc)

                # 更新退订单状态
                refund = self.set_refund_success(
                    refund=refund, refund_history_id=pay_refund.id,
                    balance_amount=pay_refund.real_refund, coupon_amount=pay_refund.coupon_refund)
                return refund
        except Exception as exc:
            if not refund:
                raise exc

            refund.status = OrderRefund.Status.FAILED.value
            refund.status_desc = str(exc)
            try:
                refund.save(update_fields=['status', 'status_desc'])
            except Exception as exc:
                pass

            return refund

    @staticmethod
    def set_refund_success(
            refund: OrderRefund, refund_history_id: str, balance_amount: Decimal, coupon_amount: Decimal
    ):
        """
        次函数需在一个事务中执行
        """
        refund.balance_amount = balance_amount
        refund.coupon_amount = coupon_amount
        refund.refund_history_id = refund_history_id
        refund.status = OrderRefund.Status.REFUNDED.value
        refund.status_desc = _('退订成功')
        refund.save(update_fields=[
            'balance_amount', 'coupon_amount', 'refund_history_id', 'status', 'status_desc'])
        is_part_refund = refund.refund_amount < refund.order.pay_amount
        OrderManager.set_order_refund_success(order=refund.order, is_part_refund=is_part_refund)
        return refund
